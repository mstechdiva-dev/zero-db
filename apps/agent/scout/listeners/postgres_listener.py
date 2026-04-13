import asyncio
import dataclasses
import logging
import os
import ssl
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import asyncpg

from scout.listeners.base_listener import BaseListener

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds — fallback when pg_notify is unavailable

# Delays (seconds) between successive reconnect attempts: 5 → 10 → 20 → 30 → 60
_RECONNECT_DELAYS = (5, 10, 20, 30, 60)

# Hostnames (suffix match) that always require SSL when sslmode is absent.
# Maps suffix → sslmode to apply.
_SSL_REQUIRED_HOSTS: dict[str, str] = {
    ".neon.tech":               "require",
    ".supabase.co":             "require",
    ".supabase.in":             "require",
    ".rds.amazonaws.com":       "require",
    ".heroku.com":              "require",
    ".elephantsql.com":         "require",
    ".timescaledb.io":          "require",
    ".cockroachlabs.cloud":     "verify-full",
    ".cockroachdb.com":         "verify-full",
}

# Port used by Supabase's PgBouncer transaction-mode pooler.
_SUPABASE_POOLER_PORT = 6543

SNAPSHOT_QUERY = """
SELECT
    c.table_schema,
    c.table_name,
    c.column_name,
    c.data_type,
    c.is_nullable,
    c.column_default,
    c.character_maximum_length,
    c.numeric_precision
FROM information_schema.columns c
JOIN information_schema.tables t
    ON c.table_schema = t.table_schema AND c.table_name = t.table_name
WHERE c.table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
  AND t.table_type = 'BASE TABLE'
ORDER BY c.table_schema, c.table_name, c.ordinal_position;
"""

INDEX_QUERY = """
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
ORDER BY schemaname, tablename, indexname;
"""

CONSTRAINT_QUERY = """
SELECT
    tc.constraint_schema,
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.constraint_schema = kcu.constraint_schema
WHERE tc.constraint_schema NOT IN ('information_schema', 'pg_catalog')
ORDER BY tc.constraint_schema, tc.table_name, tc.constraint_name;
"""

NOTIFY_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION schemazero_notify_ddl()
RETURNS event_trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_notify('schemazero_ddl', TG_TAG);
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_event_trigger WHERE evtname = 'schemazero_ddl_watcher'
    ) THEN
        CREATE EVENT TRIGGER schemazero_ddl_watcher
        ON ddl_command_end
        EXECUTE FUNCTION schemazero_notify_ddl();
    END IF;
END;
$$;
"""


@dataclasses.dataclass(frozen=True)
class _ConnConfig:
    dsn: str
    ssl_arg: object       # None | False | ssl.SSLContext
    provider: str         # e.g. "neon", "supabase", "cockroachdb", "local", "generic"
    is_pooler: bool       # True = PgBouncer transaction-mode (no LISTEN, stmt_cache=0)


def _sslmode_to_arg(sslmode: Optional[str]) -> object:
    """Convert a libpq sslmode string to the asyncpg ``ssl`` kwarg value."""
    if sslmode == "disable":
        return False
    if sslmode == "require":
        # Encrypt but skip cert/hostname check — matches libpq "require" semantics.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    if sslmode == "verify-ca":
        # Verify the certificate chain, but do not enforce hostname matching.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_REQUIRED
        return ctx
    if sslmode == "verify-full":
        # Full chain + hostname verification.
        return ssl.create_default_context()
    # prefer / allow / None → let asyncpg decide
    return None


def _parse_connection(connection_string: str) -> _ConnConfig:
    """Normalise a Postgres DSN and derive connection options for asyncpg.

    Handles every deployment model automatically:

    Local
        ``postgresql://user:pass@localhost/db`` — no SSL, plain connection.

    Cloud (Neon, Supabase direct, RDS, Heroku, ElephantSQL, Timescale …)
        SSL defaults are applied from the host suffix even when ``sslmode``
        is absent from the URL, so users can paste a bare connection string.

    Serverless / pooled (Supabase PgBouncer on port 6543)
        Detected as ``is_pooler=True``.  The caller must set
        ``statement_cache_size=0`` and skip ``LISTEN``/``NOTIFY``.

    CockroachDB
        Detected from host suffix; ``sslmode=verify-full`` applied by default.

    asyncpg does **not** parse ``sslmode`` from the DSN query string —
    leaving it there raises ``invalid connection parameter``.  This function
    strips it and converts it to the correct ``ssl`` kwarg instead.
    """
    # Normalise postgres:// → postgresql://
    dsn = connection_string
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]

    parsed = urlparse(dsn)
    host = (parsed.hostname or "").lower()
    port = parsed.port

    # Strip sslmode from query string so asyncpg doesn't reject it
    qs = parse_qs(parsed.query, keep_blank_values=True)
    explicit_sslmode: Optional[str] = qs.pop("sslmode", [None])[0]
    clean_query = urlencode({k: v[0] for k, v in qs.items()})
    dsn = urlunparse(parsed._replace(query=clean_query))

    # Detect provider and pooler from hostname / port
    provider = "generic"
    is_pooler = False

    if host in ("localhost", "127.0.0.1", "::1") or not host:
        provider = "local"
    else:
        for suffix, _ in _SSL_REQUIRED_HOSTS.items():
            if host.endswith(suffix):
                provider = suffix.lstrip(".").split(".")[0]  # e.g. "neon", "supabase"
                break
        # Supabase PgBouncer pooler is always on port 6543
        if port == _SUPABASE_POOLER_PORT or "pooler" in host:
            is_pooler = True

    # Determine effective sslmode: explicit value wins; fall back to host default
    sslmode = explicit_sslmode
    if sslmode is None and provider != "local":
        for suffix, default_mode in _SSL_REQUIRED_HOSTS.items():
            if host.endswith(suffix):
                sslmode = default_mode
                break

    ssl_arg = _sslmode_to_arg(sslmode)
    return _ConnConfig(dsn=dsn, ssl_arg=ssl_arg, provider=provider, is_pooler=is_pooler)


class PostgresListener(BaseListener):
    """Scout listener for PostgreSQL — local, cloud, serverless, and pooled.

    Supported setups (detected automatically from the connection string):

    * **Local** — plain TCP, no SSL required
    * **Cloud** — Neon, Supabase (direct), RDS, Heroku, ElephantSQL, Timescale,
      CockroachDB: SSL defaults applied from hostname; users can paste a bare
      connection string without adding ``?sslmode=…`` manually
    * **Serverless** — Neon auto-pause: connection is re-established automatically
      with exponential backoff whenever the compute wakes up after being idle
    * **Pooled / PgBouncer** — Supabase port 6543 (transaction-mode pooler):
      ``statement_cache_size=0`` is set; ``LISTEN``/``NOTIFY`` is skipped in
      favour of polling because PgBouncer does not forward ``LISTEN`` commands

    Change detection strategy (in priority order):
      1. ``pg_notify`` via a DDL event trigger (lowest latency)
      2. Polling ``information_schema`` every ``POLL_INTERVAL`` seconds
         (fallback when the trigger cannot be installed, or when using a pooler)
    """

    def __init__(self, database_id: str, org_id: str, supabase_client):
        super().__init__(database_id, org_id, supabase_client)
        self._conn: Optional[asyncpg.Connection] = None
        self._cfg: Optional[_ConnConfig] = None
        self._connection_string: str = ""
        self._last_snapshot: Optional[dict] = None
        self._internal_url = os.environ.get("INTERNAL_API_URL", "http://localhost:8000")
        self._use_notify = True

    async def connect(self, connection_string: str) -> None:
        self._connection_string = connection_string
        cfg = _parse_connection(connection_string)
        self._cfg = cfg

        kwargs: dict = {"timeout": 30}
        if cfg.ssl_arg is not None:
            kwargs["ssl"] = cfg.ssl_arg
        if cfg.is_pooler:
            # PgBouncer transaction mode does not support prepared statements
            kwargs["statement_cache_size"] = 0

        self._conn = await asyncpg.connect(cfg.dsn, **kwargs)
        logger.info(
            "PostgresListener connected to database_id=%s (provider=%s, pooler=%s)",
            self.database_id,
            cfg.provider,
            cfg.is_pooler,
        )

    async def capture_snapshot(self) -> dict:
        if not self._conn:
            return {}

        columns = await self._conn.fetch(SNAPSHOT_QUERY)
        indexes = await self._conn.fetch(INDEX_QUERY)
        constraints = await self._conn.fetch(CONSTRAINT_QUERY)

        return {
            "columns": [dict(r) for r in columns],
            "indexes": [dict(r) for r in indexes],
            "constraints": [dict(r) for r in constraints],
        }

    async def _try_install_notify(self) -> bool:
        """Attempt to install the DDL event trigger. Returns True on success."""
        try:
            await self._conn.execute(NOTIFY_FUNCTION_SQL)
            return True
        except Exception as exc:
            logger.info(
                "pg_notify setup failed for db=%s (falling back to polling): %s",
                self.database_id,
                exc,
            )
            return False

    async def listen(self) -> None:
        if not self._conn or not self._cfg:
            raise RuntimeError("PostgresListener.connect() must be called first")

        self.start_heartbeat()
        self._last_snapshot = await self.capture_snapshot()

        # PgBouncer transaction mode does not forward LISTEN commands — go
        # straight to polling so we never waste a connection attempt on it.
        if self._cfg.is_pooler:
            self._use_notify = False
            logger.info(
                "Pooler detected for db=%s — using polling (LISTEN not supported through PgBouncer)",
                self.database_id,
            )
        else:
            self._use_notify = await self._try_install_notify()

        if self._use_notify:
            await self._listen_notify()
        else:
            await self._listen_polling()

    # ------------------------------------------------------------------
    # pg_notify path (with reconnect for serverless / auto-pause)
    # ------------------------------------------------------------------

    async def _listen_notify(self) -> None:
        """Listen for DDL changes via pg_notify, reconnecting on connection loss."""
        self._running = True
        while self._running:
            try:
                await self._subscribe_and_wait()
            except (
                asyncpg.PostgresConnectionStatusError,
                asyncpg.ConnectionDoesNotExistError,
                OSError,
            ) as exc:
                if not self._running:
                    break
                logger.warning(
                    "pg_notify connection lost for db=%s: %s — attempting reconnect",
                    self.database_id,
                    exc,
                )
                reconnected = await self._reconnect()
                if reconnected:
                    if not await self._try_install_notify():
                        logger.info(
                            "Falling back to polling after reconnect for db=%s",
                            self.database_id,
                        )
                        await self._listen_polling()
                        return
                else:
                    logger.error(
                        "All reconnect attempts failed for db=%s — stopping listener",
                        self.database_id,
                    )
                    self._running = False

    async def _subscribe_and_wait(self) -> None:
        """Register the pg_notify listener and block until stopped or disconnected."""

        async def on_notification(conn, pid, channel, payload):
            logger.info("DDL event received on db=%s: %s", self.database_id, payload)
            await self._handle_change()

        await self._conn.add_listener("schemazero_ddl", on_notification)
        logger.info("pg_notify listener active for db=%s", self.database_id)
        try:
            while self._running:
                if self._conn.is_closed():
                    raise asyncpg.ConnectionDoesNotExistError(
                        "Connection closed unexpectedly"
                    )
                await asyncio.sleep(1)
        finally:
            if not self._conn.is_closed():
                await self._conn.remove_listener("schemazero_ddl", on_notification)

    # ------------------------------------------------------------------
    # Polling path (with reconnect)
    # ------------------------------------------------------------------

    async def _listen_polling(self) -> None:
        """Poll information_schema on a fixed interval, reconnecting on connection loss."""
        logger.info(
            "Polling listener active for db=%s every %ds", self.database_id, POLL_INTERVAL
        )
        self._running = True
        while self._running:
            await asyncio.sleep(POLL_INTERVAL)
            try:
                await self._handle_change()
            except (
                asyncpg.PostgresConnectionStatusError,
                asyncpg.ConnectionDoesNotExistError,
                OSError,
            ) as exc:
                if not self._running:
                    break
                logger.warning(
                    "Polling connection lost for db=%s: %s — attempting reconnect",
                    self.database_id,
                    exc,
                )
                reconnected = await self._reconnect()
                if not reconnected:
                    logger.error(
                        "All reconnect attempts failed for db=%s — stopping listener",
                        self.database_id,
                    )
                    self._running = False

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    async def _handle_change(self) -> None:
        """Capture after-snapshot, diff against before, write events."""
        before = self._last_snapshot or {}
        after = await self.capture_snapshot()

        changes = _diff_snapshots(before, after)
        for change in changes:
            event_id = await self.write_change_event(
                change_type=change["change_type"],
                object_type=change["object_type"],
                object_name=change["object_name"],
                schema_name=change.get("schema_name"),
                before_state=change.get("before_state"),
                after_state=change.get("after_state"),
            )
            if event_id:
                await self.trigger_zero(event_id, self._internal_url)

        self._last_snapshot = after

    async def _reconnect(self) -> bool:
        """Re-establish the database connection with exponential backoff.

        Tries up to ``len(_RECONNECT_DELAYS)`` times.  Returns True if a
        connection is successfully restored, False if all attempts fail.
        """
        for delay in _RECONNECT_DELAYS:
            logger.info(
                "Reconnecting to db=%s in %ds...", self.database_id, delay
            )
            await asyncio.sleep(delay)
            try:
                if self._conn and not self._conn.is_closed():
                    await self._conn.close()
                await self.connect(self._connection_string)
                logger.info("Reconnected to db=%s", self.database_id)
                return True
            except Exception as exc:
                logger.warning(
                    "Reconnect attempt failed for db=%s: %s", self.database_id, exc
                )
        return False

    async def disconnect(self) -> None:
        await self.stop_heartbeat()
        self._running = False
        if self._conn and not self._conn.is_closed():
            await self._conn.close()
            self._conn = None
        logger.info("PostgresListener disconnected from db=%s", self.database_id)


# ---------------------------------------------------------------------------
# Internal diff helpers
# ---------------------------------------------------------------------------

def _snapshot_column_key(col: dict) -> str:
    return f"{col['table_schema']}.{col['table_name']}.{col['column_name']}"


def _diff_snapshots(before: dict, after: dict) -> list[dict]:
    """Compare two schema snapshots and return a list of change dicts."""
    changes: list[dict] = []

    before_cols = {_snapshot_column_key(c): c for c in before.get("columns", [])}
    after_cols = {_snapshot_column_key(c): c for c in after.get("columns", [])}

    # Columns added
    for key, col in after_cols.items():
        if key not in before_cols:
            changes.append(
                {
                    "change_type": "column_added",
                    "object_type": "column",
                    "object_name": col["column_name"],
                    "schema_name": col["table_schema"],
                    "before_state": None,
                    "after_state": col,
                }
            )

    # Columns dropped
    for key, col in before_cols.items():
        if key not in after_cols:
            changes.append(
                {
                    "change_type": "column_dropped",
                    "object_type": "column",
                    "object_name": col["column_name"],
                    "schema_name": col["table_schema"],
                    "before_state": col,
                    "after_state": None,
                }
            )

    # Columns modified
    for key in before_cols:
        if key in after_cols and before_cols[key] != after_cols[key]:
            changes.append(
                {
                    "change_type": "column_modified",
                    "object_type": "column",
                    "object_name": before_cols[key]["column_name"],
                    "schema_name": before_cols[key]["table_schema"],
                    "before_state": before_cols[key],
                    "after_state": after_cols[key],
                }
            )

    # Tables: derive from column sets
    before_tables = {
        f"{c['table_schema']}.{c['table_name']}" for c in before.get("columns", [])
    }
    after_tables = {
        f"{c['table_schema']}.{c['table_name']}" for c in after.get("columns", [])
    }

    for table in after_tables - before_tables:
        schema, name = table.split(".", 1)
        changes.append(
            {
                "change_type": "table_created",
                "object_type": "table",
                "object_name": name,
                "schema_name": schema,
                "before_state": None,
                "after_state": {"table": table},
            }
        )

    for table in before_tables - after_tables:
        schema, name = table.split(".", 1)
        changes.append(
            {
                "change_type": "table_dropped",
                "object_type": "table",
                "object_name": name,
                "schema_name": schema,
                "before_state": {"table": table},
                "after_state": None,
            }
        )

    # Indexes
    def _idx_key(i: dict) -> str:
        return f"{i.get('schemaname')}.{i.get('tablename')}.{i.get('indexname')}"

    before_idx = {_idx_key(i): i for i in before.get("indexes", [])}
    after_idx = {_idx_key(i): i for i in after.get("indexes", [])}

    for name, idx in after_idx.items():
        if name not in before_idx:
            changes.append(
                {
                    "change_type": "index_created",
                    "object_type": "index",
                    "object_name": name,
                    "schema_name": idx.get("schemaname"),
                    "before_state": None,
                    "after_state": idx,
                }
            )

    for name, idx in before_idx.items():
        if name not in after_idx:
            changes.append(
                {
                    "change_type": "index_dropped",
                    "object_type": "index",
                    "object_name": name,
                    "schema_name": idx.get("schemaname"),
                    "before_state": idx,
                    "after_state": None,
                }
            )

    # Constraints
    def _con_key(c: dict) -> str:
        return f"{c.get('constraint_schema')}.{c.get('table_name')}.{c.get('constraint_name')}"

    before_con = {_con_key(c): c for c in before.get("constraints", [])}
    after_con = {_con_key(c): c for c in after.get("constraints", [])}

    for name, con in after_con.items():
        if name not in before_con:
            changes.append(
                {
                    "change_type": "constraint_added",
                    "object_type": "constraint",
                    "object_name": name,
                    "schema_name": con.get("constraint_schema"),
                    "before_state": None,
                    "after_state": con,
                }
            )

    for name, con in before_con.items():
        if name not in after_con:
            changes.append(
                {
                    "change_type": "constraint_dropped",
                    "object_type": "constraint",
                    "object_name": name,
                    "schema_name": con.get("constraint_schema"),
                    "before_state": con,
                    "after_state": None,
                }
            )

    return changes
