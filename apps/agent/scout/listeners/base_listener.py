import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 30  # seconds


class BaseListener(ABC):
    """Abstract base class for all Scout database engine listeners.

    Every listener must implement connect(), listen(), capture_snapshot(),
    and disconnect(). Shared heartbeat logic is provided here so all
    listeners update Supabase on the same schedule.
    """

    def __init__(self, database_id: str, org_id: str, supabase_client):
        self.database_id = database_id
        self.org_id = org_id
        self.supabase = supabase_client
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Abstract interface — each engine must implement these
    # ------------------------------------------------------------------

    @abstractmethod
    async def connect(self, connection_string: str) -> None:
        """Establish a connection to the target database."""

    @abstractmethod
    async def listen(self) -> None:
        """Start listening for schema changes. Runs until stopped."""

    @abstractmethod
    async def capture_snapshot(self) -> dict:
        """Return a JSON-serialisable dict representing the current schema."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanly close the database connection."""

    # ------------------------------------------------------------------
    # Shared heartbeat logic
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        while self._running:
            await self._update_heartbeat(status="active")
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def _update_heartbeat(self, status: str = "active") -> None:
        try:
            self.supabase.table("scout_heartbeat").upsert(
                {
                    "database_id": self.database_id,
                    "org_id": self.org_id,
                    "status": status,
                    "last_seen_at": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                    ),
                }
            ).execute()
        except Exception as exc:
            logger.warning("Heartbeat update failed for %s: %s", self.database_id, exc)

    def start_heartbeat(self) -> None:
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        await self._update_heartbeat(status="offline")

    # ------------------------------------------------------------------
    # Shared change event writer
    # ------------------------------------------------------------------

    async def write_change_event(
        self,
        change_type: str,
        object_type: str,
        object_name: str,
        before_state: Optional[dict],
        after_state: Optional[dict],
        schema_name: Optional[str] = None,
    ) -> Optional[str]:
        """Write a detected change to Supabase and return the new event ID."""
        try:
            result = (
                self.supabase.table("change_events")
                .insert(
                    {
                        "org_id": self.org_id,
                        "database_id": self.database_id,
                        "change_type": change_type,
                        "object_type": object_type,
                        "object_name": object_name,
                        "schema_name": schema_name,
                        "before_state": before_state,
                        "after_state": after_state,
                    }
                )
                .execute()
            )
            if result.data:
                return result.data[0]["id"]
        except Exception as exc:
            logger.error(
                "Failed to write change_event for db=%s: %s", self.database_id, exc
            )
        return None

    # ------------------------------------------------------------------
    # Zero trigger
    # ------------------------------------------------------------------

    async def trigger_zero(self, change_event_id: str, internal_url: str) -> None:
        """Notify Zero to analyze the new change event."""
        import httpx

        headers: dict[str, str] = {}
        secret = os.environ.get("INTERNAL_API_SECRET", "")
        if secret:
            headers["X-Internal-Secret"] = secret

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{internal_url}/internal/analyze",
                    json={"change_event_id": change_event_id},
                    headers=headers,
                    timeout=5,
                )
        except Exception as exc:
            logger.warning(
                "Zero trigger failed for event %s: %s", change_event_id, exc
            )
