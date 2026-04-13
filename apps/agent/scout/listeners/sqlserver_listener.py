# NOT_IMPLEMENTED — SQL Server listener is coming soon.
#
# This stub exists so ScoutRunner can reference the class without crashing.
# When ready, implement SQLServerListener by inheriting from BaseListener and
# polling sys.objects / sys.columns in information_schema for schema changes.
#
# Required package: aioodbc or pyodbc wrapped with asyncio.to_thread

from scout.listeners.base_listener import BaseListener


class SQLServerListener(BaseListener):
    """Scout listener for Microsoft SQL Server — NOT YET IMPLEMENTED."""

    async def connect(self, connection_string: str) -> None:
        raise NotImplementedError(
            "SQLServerListener is not yet implemented. "
            "Remove this stub and build the full listener when SQL Server support is added."
        )

    async def listen(self) -> None:
        raise NotImplementedError("SQLServerListener is not yet implemented.")

    async def capture_snapshot(self) -> dict:
        raise NotImplementedError("SQLServerListener is not yet implemented.")

    async def disconnect(self) -> None:
        raise NotImplementedError("SQLServerListener is not yet implemented.")
