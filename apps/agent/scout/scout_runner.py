"""Scout Runner — main orchestrator for all database listeners.

ScoutRunner starts on FastAPI startup and maintains a live listener for every
active connected_database in Supabase. It polls Supabase periodically to pick
up newly added databases and drops listeners for removed ones.
"""

import asyncio
import logging
import os
from typing import Optional

from services.encryption_service import EncryptionService
from services.supabase_service import get_supabase

logger = logging.getLogger(__name__)

POLL_INTERVAL = 60  # seconds — how often to check for new/removed databases

LISTENER_CLASSES = {
    "postgresql": "scout.listeners.postgres_listener.PostgresListener",
    "supabase": "scout.listeners.postgres_listener.PostgresListener",
    "neon": "scout.listeners.postgres_listener.PostgresListener",
    "cockroachdb": "scout.listeners.postgres_listener.PostgresListener",
    "mysql": "scout.listeners.mysql_listener.MySQLListener",
    "mariadb": "scout.listeners.mysql_listener.MySQLListener",
    "mongodb": "scout.listeners.mongodb_listener.MongoDBListener",
    "redis": "scout.listeners.redis_listener.RedisListener",
}


def _import_listener_class(dotted_path: str):
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class ScoutRunner:
    """Manages a pool of engine listeners, one per active connected database."""

    def __init__(self):
        self._listeners: dict[str, asyncio.Task] = {}  # database_id -> task
        self._enc = EncryptionService()
        self._running = False

    async def run(self) -> None:
        """Main loop — polls Supabase for database list and reconciles listeners."""
        self._running = True
        logger.info("ScoutRunner started")

        while self._running:
            try:
                await self._reconcile()
            except Exception as exc:
                logger.error("ScoutRunner reconcile error: %s", exc)
            await asyncio.sleep(POLL_INTERVAL)

    async def stop(self) -> None:
        self._running = False
        for database_id, task in list(self._listeners.items()):
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._listeners.clear()
        logger.info("ScoutRunner stopped")

    async def _reconcile(self) -> None:
        """Start listeners for new databases and remove stale ones."""
        supabase = get_supabase()
        result = (
            supabase.table("connected_databases")
            .select("id, org_id, engine, encrypted_connection_string")
            .eq("is_active", True)
            .execute()
        )
        active_databases = result.data or []
        active_ids = {db["id"] for db in active_databases}

        # Stop listeners for removed databases
        for database_id in list(self._listeners.keys()):
            if database_id not in active_ids:
                logger.info("Stopping listener for removed db=%s", database_id)
                task = self._listeners.pop(database_id)
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

        # Start listeners for new databases
        for db in active_databases:
            if db["id"] not in self._listeners:
                await self._start_listener(db)

    async def _start_listener(self, db: dict) -> None:
        database_id = db["id"]
        engine = db["engine"].lower()

        listener_path = LISTENER_CLASSES.get(engine)
        if not listener_path:
            logger.warning("No listener available for engine '%s' (db=%s)", engine, database_id)
            return

        try:
            ListenerClass = _import_listener_class(listener_path)
        except (ImportError, AttributeError) as exc:
            logger.error("Failed to import listener for engine '%s': %s", engine, exc)
            return

        try:
            conn_string = self._enc.decrypt(db["encrypted_connection_string"])
        except Exception as exc:
            logger.error("Failed to decrypt connection string for db=%s: %s", database_id, exc)
            return

        supabase = get_supabase()
        listener = ListenerClass(
            database_id=database_id,
            org_id=db["org_id"],
            supabase_client=supabase,
        )

        task = asyncio.create_task(
            self._run_listener(listener, conn_string, database_id)
        )
        self._listeners[database_id] = task
        logger.info("Started %s listener for db=%s", engine, database_id)

    async def _run_listener(self, listener, conn_string: str, database_id: str) -> None:
        """Connect and run a listener, with automatic reconnection on failure."""
        backoff = 5
        while self._running:
            try:
                await listener.connect(conn_string)
                backoff = 5  # reset on successful connect
                await listener.listen()
            except asyncio.CancelledError:
                await listener.disconnect()
                return
            except Exception as exc:
                logger.error(
                    "Listener error for db=%s: %s — retrying in %ds",
                    database_id,
                    exc,
                    backoff,
                )
                try:
                    await listener.disconnect()
                except Exception:
                    pass
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 300)
