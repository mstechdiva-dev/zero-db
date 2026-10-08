"""Names the listeners take from their database drivers must exist.

An except clause that names a missing exception class does not fail when the
file loads. It fails later, at the worst moment: while handling a lost
connection. So check every `asyncpg.Something` the Postgres listener uses.
"""

import re
from pathlib import Path

import asyncpg

LISTENER = Path(__file__).resolve().parents[1] / "scout" / "listeners" / "postgres_listener.py"


def test_every_asyncpg_name_the_postgres_listener_uses_exists():
    names = set(re.findall(r"\basyncpg\.([A-Za-z_]+)", LISTENER.read_text(encoding="utf-8")))
    assert {"connect", "PostgresConnectionError", "ConnectionDoesNotExistError"} <= names
    missing = sorted(n for n in names if not hasattr(asyncpg, n))
    assert not missing, f"asyncpg has no {missing}"
