import asyncio
import json
import logging
import os
from typing import Optional

import asyncpg

from scout.listeners.base_listener import BaseListener

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds — fallback when pg_notify is unavailable

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


class PostgresListener(BaseListener):
    """Scout listener for PostgreSQL, Supabase, Neon, and CockroachDB.

    Uses pg_notify via an event trigger when possible; falls back to polling
    information_schema every POLL_INTERVAL seconds if the trigger cannot be
    installed (e.g., insufficient privileges or hosted environments that
    block event trigger creation).
    """

    def __init__(self, database_id: str, org_id: str, supabase_client):
        super().__init__(database_id, org_id, supabase_client)
        self._conn: Optional[asyncpg.Connection] = None
        self._last_snapshot: Optional[dict] = None
        self._internal_url = os.environ.get("INTERNAL_API_URL", "http://localhost:8000")
        self._use_notify = True

    async def connect(self, connection_string: str) -> None:
        self._conn = await asyncpg.connect(connection_string)
        logger.info("PostgresListener connected to database_id=%s", self.database_id)

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
        if not self._conn:
            raise RuntimeError("PostgresListener.connect() must be called first")

        self.start_heartbeat()
        self._last_snapshot = await self.capture_snapshot()
        self._use_notify = await self._try_install_notify()

        if self._use_notify:
            await self._listen_notify()
        else:
            await self._listen_polling()

    async def _listen_notify(self) -> None:
        """Listen for DDL changes via pg_notify channel."""

        async def on_notification(conn, pid, channel, payload):
            logger.info(
                "DDL event received on db=%s: %s", self.database_id, payload
            )
            await self._handle_change()

        await self._conn.add_listener("schemazero_ddl", on_notification)
        logger.info("pg_notify listener active for db=%s", self.database_id)

        self._running = True
        while self._running:
            await asyncio.sleep(1)

        await self._conn.remove_listener("schemazero_ddl", on_notification)

    async def _listen_polling(self) -> None:
        """Poll information_schema on a fixed interval."""
        logger.info("Polling listener active for db=%s every %ds", self.database_id, POLL_INTERVAL)
        self._running = True
        while self._running:
            await asyncio.sleep(POLL_INTERVAL)
            await self._handle_change()

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

    async def disconnect(self) -> None:
        await self.stop_heartbeat()
        if self._conn:
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
