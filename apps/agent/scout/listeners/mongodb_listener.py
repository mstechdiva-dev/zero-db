import asyncio
import logging
import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from scout.listeners.base_listener import BaseListener

logger = logging.getLogger(__name__)


class MongoDBListener(BaseListener):
    """Scout listener for MongoDB.

    Uses change streams on the admin database to detect collection and index
    changes. Watches for: createCollection, dropCollection, createIndexes,
    dropIndexes.
    """

    def __init__(self, database_id: str, org_id: str, supabase_client):
        super().__init__(database_id, org_id, supabase_client)
        self._client: Optional[AsyncIOMotorClient] = None
        self._db_name: Optional[str] = None
        self._internal_url = os.environ.get("INTERNAL_API_URL", "http://localhost:8000")

    async def connect(self, connection_string: str) -> None:
        from urllib.parse import urlparse

        parsed = urlparse(connection_string)
        self._db_name = parsed.path.lstrip("/") or "admin"
        self._client = AsyncIOMotorClient(connection_string)
        # Verify connectivity
        await self._client.admin.command("ping")
        logger.info("MongoDBListener connected to database_id=%s", self.database_id)

    async def capture_snapshot(self) -> dict:
        if not self._client:
            return {}

        db = self._client[self._db_name]
        collections = await db.list_collection_names()

        snapshot: dict = {}
        for col_name in collections:
            collection = db[col_name]
            indexes = await collection.index_information()
            snapshot[col_name] = {"indexes": indexes}

        return {"collections": snapshot}

    async def listen(self) -> None:
        if not self._client:
            raise RuntimeError("MongoDBListener.connect() must be called first")

        self.start_heartbeat()
        self._last_snapshot = await self.capture_snapshot()

        logger.info("MongoDBListener change stream active for db=%s", self.database_id)

        pipeline = [
            {
                "$match": {
                    "operationType": {
                        "$in": [
                            "createCollection",
                            "dropCollection",
                            "createIndexes",
                            "dropIndexes",
                        ]
                    }
                }
            }
        ]

        self._running = True
        db = self._client[self._db_name]
        async with db.watch(pipeline) as stream:
            while self._running:
                try:
                    change = await asyncio.wait_for(stream.next(), timeout=5.0)
                    await self._handle_mongo_change(change)
                except asyncio.TimeoutError:
                    continue
                except Exception as exc:
                    logger.error("MongoDBListener stream error for db=%s: %s", self.database_id, exc)
                    await asyncio.sleep(5)

    async def _handle_mongo_change(self, change: dict) -> None:
        op = change.get("operationType", "")
        ns = change.get("ns", {})
        collection_name = ns.get("coll", "unknown")

        before = self._last_snapshot or {}
        after = await self.capture_snapshot()

        change_type_map = {
            "createCollection": "table_created",
            "dropCollection": "table_dropped",
            "createIndexes": "index_created",
            "dropIndexes": "index_dropped",
        }
        change_type = change_type_map.get(op, "schema_change")
        object_type = "collection" if "Collection" in op else "index"

        before_state = before.get("collections", {}).get(collection_name)
        after_state = after.get("collections", {}).get(collection_name)

        event_id = await self.write_change_event(
            change_type=change_type,
            object_type=object_type,
            object_name=collection_name,
            schema_name=self._db_name,
            before_state=before_state,
            after_state=after_state,
        )
        if event_id:
            await self.trigger_zero(event_id, self._internal_url)

        self._last_snapshot = after

    async def disconnect(self) -> None:
        await self.stop_heartbeat()
        self._running = False
        if self._client:
            self._client.close()
            self._client = None
        logger.info("MongoDBListener disconnected from db=%s", self.database_id)
