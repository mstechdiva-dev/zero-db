# NOT_IMPLEMENTED — Snowflake listener is coming soon.
#
# This stub exists so ScoutRunner can reference the class without crashing.
# When ready, implement SnowflakeListener by inheriting from BaseListener and
# polling INFORMATION_SCHEMA.TABLES / INFORMATION_SCHEMA.COLUMNS for schema
# changes.
#
# Required package: snowflake-connector-python with asyncio.to_thread wrapping

from scout.listeners.base_listener import BaseListener


class SnowflakeListener(BaseListener):
    """Scout listener for Snowflake — NOT YET IMPLEMENTED."""

    async def connect(self, connection_string: str) -> None:
        raise NotImplementedError(
            "SnowflakeListener is not yet implemented. "
            "Remove this stub and build the full listener when Snowflake support is added."
        )

    async def listen(self) -> None:
        raise NotImplementedError("SnowflakeListener is not yet implemented.")

    async def capture_snapshot(self) -> dict:
        raise NotImplementedError("SnowflakeListener is not yet implemented.")

    async def disconnect(self) -> None:
        raise NotImplementedError("SnowflakeListener is not yet implemented.")
