"""Schema snapshot utilities shared across Scout listeners.

Each listener captures its own engine-specific snapshot format. This module
provides shared serialisation and storage helpers so that snapshots can be
stored alongside change events in a consistent JSON structure.
"""

import json
import time
from typing import Any


def serialise(snapshot: Any) -> str:
    """Return a compact JSON string of a snapshot dict."""
    return json.dumps(snapshot, default=str, separators=(",", ":"))


def deserialise(raw: str) -> Any:
    """Parse a JSON snapshot string back to a Python object."""
    return json.loads(raw)


def timestamp_snapshot(snapshot: dict) -> dict:
    """Wrap a snapshot with a captured_at timestamp."""
    return {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": snapshot,
    }


def flatten_postgres_snapshot(snapshot: dict) -> dict:
    """Flatten a PostgreSQL snapshot into a table-keyed structure.

    Useful when you want to look up a table's full column list quickly.
    """
    tables: dict[str, dict] = {}
    for col in snapshot.get("columns", []):
        key = f"{col['table_schema']}.{col['table_name']}"
        tables.setdefault(key, {"columns": [], "indexes": [], "constraints": []})
        tables[key]["columns"].append(col)

    for idx in snapshot.get("indexes", []):
        key = f"{idx['schemaname']}.{idx['tablename']}"
        if key in tables:
            tables[key]["indexes"].append(idx)

    for con in snapshot.get("constraints", []):
        key = f"{con['constraint_schema']}.{con['table_name']}"
        if key in tables:
            tables[key]["constraints"].append(con)

    return tables
