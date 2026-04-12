import asyncio
import logging
import os
from typing import Optional

import aioredis

from scout.listeners.base_listener import BaseListener

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds


class RedisListener(BaseListener):
    """Scout listener for Redis.

    Enables keyspace notifications and monitors key pattern changes at
    namespace level (not individual keys). Polls every POLL_INTERVAL seconds
    using SCAN with pattern matching to detect new or dropped key namespaces
    and type changes.
    """

    def __init__(self, database_id: str, org_id: str, supabase_client):
        super().__init__(database_id, org_id, supabase_client)
        self._redis: Optional[aioredis.Redis] = None
        self._last_snapshot: Optional[dict] = None
        self._internal_url = os.environ.get("INTERNAL_API_URL", "http://localhost:8000")

    async def connect(self, connection_string: str) -> None:
        self._redis = await aioredis.from_url(connection_string, decode_responses=True)
        # Enable keyspace notifications (KEA = Keyspace + Keyevent + All events)
        try:
            await self._redis.config_set("notify-keyspace-events", "KEA")
        except Exception as exc:
            logger.warning(
                "Could not enable keyspace notifications for db=%s: %s",
                self.database_id,
                exc,
            )
        logger.info("RedisListener connected to database_id=%s", self.database_id)

    async def capture_snapshot(self) -> dict:
        """Scan all keys and group them into namespace patterns."""
        if not self._redis:
            return {}

        namespaces: dict[str, dict] = {}
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, count=500)
            for key in keys:
                namespace = key.split(":")[0] if ":" in key else key
                if namespace not in namespaces:
                    key_type = await self._redis.type(key)
                    ttl = await self._redis.ttl(key)
                    namespaces[namespace] = {
                        "type": key_type,
                        "has_ttl": ttl > 0,
                        "sample_key": key,
                    }
            if cursor == 0:
                break

        return {"namespaces": namespaces}

    async def listen(self) -> None:
        if not self._redis:
            raise RuntimeError("RedisListener.connect() must be called first")

        self.start_heartbeat()
        self._last_snapshot = await self.capture_snapshot()
        logger.info(
            "RedisListener polling every %ds for db=%s", POLL_INTERVAL, self.database_id
        )

        self._running = True
        while self._running:
            await asyncio.sleep(POLL_INTERVAL)
            await self._handle_change()

    async def _handle_change(self) -> None:
        before = self._last_snapshot or {}
        after = await self.capture_snapshot()

        changes = _diff_redis_snapshots(before, after)
        for change in changes:
            event_id = await self.write_change_event(
                change_type=change["change_type"],
                object_type=change["object_type"],
                object_name=change["object_name"],
                schema_name=None,
                before_state=change.get("before_state"),
                after_state=change.get("after_state"),
            )
            if event_id:
                await self.trigger_zero(event_id, self._internal_url)

        self._last_snapshot = after

    async def disconnect(self) -> None:
        await self.stop_heartbeat()
        self._running = False
        if self._redis:
            await self._redis.close()
            self._redis = None
        logger.info("RedisListener disconnected from db=%s", self.database_id)


# ---------------------------------------------------------------------------
# Internal diff helpers
# ---------------------------------------------------------------------------

def _diff_redis_snapshots(before: dict, after: dict) -> list[dict]:
    changes: list[dict] = []

    before_ns = before.get("namespaces", {})
    after_ns = after.get("namespaces", {})

    for ns, info in after_ns.items():
        if ns not in before_ns:
            changes.append(
                {
                    "change_type": "key_pattern_added",
                    "object_type": "key_namespace",
                    "object_name": ns,
                    "before_state": None,
                    "after_state": info,
                }
            )
        elif before_ns[ns].get("type") != info.get("type"):
            changes.append(
                {
                    "change_type": "key_type_changed",
                    "object_type": "key_namespace",
                    "object_name": ns,
                    "before_state": before_ns[ns],
                    "after_state": info,
                }
            )
        elif before_ns[ns].get("has_ttl") != info.get("has_ttl"):
            changes.append(
                {
                    "change_type": "ttl_policy_changed",
                    "object_type": "key_namespace",
                    "object_name": ns,
                    "before_state": before_ns[ns],
                    "after_state": info,
                }
            )

    for ns, info in before_ns.items():
        if ns not in after_ns:
            changes.append(
                {
                    "change_type": "key_pattern_dropped",
                    "object_type": "key_namespace",
                    "object_name": ns,
                    "before_state": info,
                    "after_state": None,
                }
            )

    return changes
