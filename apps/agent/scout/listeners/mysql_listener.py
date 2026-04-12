import asyncio
import logging
import os
from typing import Optional

import aiomysql

from scout.listeners.base_listener import BaseListener

logger = logging.getLogger(__name__)

POLL_INTERVAL = 60  # seconds — per build spec for MySQL/MariaDB


class MySQLListener(BaseListener):
    """Scout listener for MySQL and MariaDB.

    Uses polling against information_schema every POLL_INTERVAL seconds.
    Snapshots are compared against the previous snapshot stored in memory;
    differences are written to Supabase as change_events.
    """

    def __init__(self, database_id: str, org_id: str, supabase_client):
        super().__init__(database_id, org_id, supabase_client)
        self._conn: Optional[aiomysql.Connection] = None
        self._last_snapshot: Optional[dict] = None
        self._internal_url = os.environ.get("INTERNAL_API_URL", "http://localhost:8000")

    async def connect(self, connection_string: str) -> None:
        """Parse a mysql://user:password@host:port/dbname URI and connect."""
        from urllib.parse import urlparse

        parsed = urlparse(connection_string)
        self._conn = await aiomysql.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 3306,
            user=parsed.username or "root",
            password=parsed.password or "",
            db=parsed.path.lstrip("/"),
            autocommit=True,
        )
        logger.info("MySQLListener connected to database_id=%s", self.database_id)

    async def capture_snapshot(self) -> dict:
        if not self._conn:
            return {}

        async with self._conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT
                    TABLE_SCHEMA,
                    TABLE_NAME,
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA NOT IN ('information_schema','performance_schema','mysql','sys')
                ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
                """
            )
            columns = await cur.fetchall()

            await cur.execute(
                """
                SELECT
                    TABLE_SCHEMA,
                    TABLE_NAME,
                    INDEX_NAME,
                    NON_UNIQUE,
                    COLUMN_NAME,
                    SEQ_IN_INDEX
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA NOT IN ('information_schema','performance_schema','mysql','sys')
                ORDER BY TABLE_SCHEMA, TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
                """
            )
            indexes = await cur.fetchall()

            await cur.execute(
                """
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA NOT IN ('information_schema','performance_schema','mysql','sys')
                  AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_SCHEMA, TABLE_NAME
                """
            )
            tables = await cur.fetchall()

        return {
            "columns": [dict(r) for r in columns],
            "indexes": [dict(r) for r in indexes],
            "tables": [dict(r) for r in tables],
        }

    async def listen(self) -> None:
        if not self._conn:
            raise RuntimeError("MySQLListener.connect() must be called first")

        self.start_heartbeat()
        self._last_snapshot = await self.capture_snapshot()
        logger.info(
            "MySQLListener polling every %ds for db=%s", POLL_INTERVAL, self.database_id
        )

        self._running = True
        while self._running:
            await asyncio.sleep(POLL_INTERVAL)
            await self._handle_change()

    async def _handle_change(self) -> None:
        before = self._last_snapshot or {}
        after = await self.capture_snapshot()

        changes = _diff_mysql_snapshots(before, after)
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
            self._conn.close()
            self._conn = None
        logger.info("MySQLListener disconnected from db=%s", self.database_id)


# ---------------------------------------------------------------------------
# Internal diff helpers
# ---------------------------------------------------------------------------

def _col_key(col: dict) -> str:
    return f"{col['TABLE_SCHEMA']}.{col['TABLE_NAME']}.{col['COLUMN_NAME']}"


def _diff_mysql_snapshots(before: dict, after: dict) -> list[dict]:
    changes: list[dict] = []

    before_cols = {_col_key(c): c for c in before.get("columns", [])}
    after_cols = {_col_key(c): c for c in after.get("columns", [])}

    for key, col in after_cols.items():
        if key not in before_cols:
            changes.append(
                {
                    "change_type": "column_added",
                    "object_type": "column",
                    "object_name": col["COLUMN_NAME"],
                    "schema_name": col["TABLE_SCHEMA"],
                    "before_state": None,
                    "after_state": col,
                }
            )

    for key, col in before_cols.items():
        if key not in after_cols:
            changes.append(
                {
                    "change_type": "column_dropped",
                    "object_type": "column",
                    "object_name": col["COLUMN_NAME"],
                    "schema_name": col["TABLE_SCHEMA"],
                    "before_state": col,
                    "after_state": None,
                }
            )

    for key in before_cols:
        if key in after_cols and before_cols[key] != after_cols[key]:
            changes.append(
                {
                    "change_type": "column_modified",
                    "object_type": "column",
                    "object_name": before_cols[key]["COLUMN_NAME"],
                    "schema_name": before_cols[key]["TABLE_SCHEMA"],
                    "before_state": before_cols[key],
                    "after_state": after_cols[key],
                }
            )

    before_tables = {
        f"{t['TABLE_SCHEMA']}.{t['TABLE_NAME']}" for t in before.get("tables", [])
    }
    after_tables = {
        f"{t['TABLE_SCHEMA']}.{t['TABLE_NAME']}" for t in after.get("tables", [])
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

    before_idx = {
        f"{i['TABLE_SCHEMA']}.{i['TABLE_NAME']}.{i['INDEX_NAME']}": i
        for i in before.get("indexes", [])
    }
    after_idx = {
        f"{i['TABLE_SCHEMA']}.{i['TABLE_NAME']}.{i['INDEX_NAME']}": i
        for i in after.get("indexes", [])
    }

    for key, idx in after_idx.items():
        if key not in before_idx:
            changes.append(
                {
                    "change_type": "index_created",
                    "object_type": "index",
                    "object_name": idx["INDEX_NAME"],
                    "schema_name": idx["TABLE_SCHEMA"],
                    "before_state": None,
                    "after_state": idx,
                }
            )

    for key, idx in before_idx.items():
        if key not in after_idx:
            changes.append(
                {
                    "change_type": "index_dropped",
                    "object_type": "index",
                    "object_name": idx["INDEX_NAME"],
                    "schema_name": idx["TABLE_SCHEMA"],
                    "before_state": idx,
                    "after_state": None,
                }
            )

    return changes
