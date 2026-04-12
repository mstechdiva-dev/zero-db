# NOT_IMPLEMENTED — Oracle listener is coming soon.
#
# This stub exists so ScoutRunner can reference the class without crashing.
# When ready, implement OracleListener by inheriting from BaseListener and
# polling ALL_OBJECTS / ALL_TAB_COLUMNS / ALL_INDEXES for schema changes.
#
# Required package: cx_Oracle or python-oracledb with asyncio.to_thread wrapping

from scout.listeners.base_listener import BaseListener


class OracleListener(BaseListener):
    """Scout listener for Oracle Database — NOT YET IMPLEMENTED."""

    async def connect(self, connection_string: str) -> None:
        raise NotImplementedError(
            "OracleListener is not yet implemented. "
            "Remove this stub and build the full listener when Oracle support is added."
        )

    async def listen(self) -> None:
        raise NotImplementedError("OracleListener is not yet implemented.")

    async def capture_snapshot(self) -> dict:
        raise NotImplementedError("OracleListener is not yet implemented.")

    async def disconnect(self) -> None:
        raise NotImplementedError("OracleListener is not yet implemented.")
