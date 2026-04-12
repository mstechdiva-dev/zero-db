"""Main schema diff orchestrator.

Routes a diff request to the correct engine differ based on the database
engine type and returns a list of DiffResult objects.
"""

from typing import Literal

from .models import DiffResult

Engine = Literal[
    "postgresql",
    "supabase",
    "neon",
    "cockroachdb",
    "mysql",
    "mariadb",
    "mongodb",
    "redis",
]


def diff(engine: str, before: dict, after: dict) -> list[DiffResult]:
    """Compare two schema snapshots using the appropriate engine differ.

    Parameters
    ----------
    engine:
        Database engine identifier (e.g. 'postgresql', 'mysql', 'mongodb').
    before:
        The schema snapshot captured before the change.
    after:
        The schema snapshot captured after the change.

    Returns
    -------
    list[DiffResult]
        One DiffResult per detected change. Empty list if snapshots are identical.

    Raises
    ------
    ValueError
        If no differ is available for the given engine.
    """
    normalized = engine.lower().strip()

    if normalized in ("postgresql", "supabase", "neon", "cockroachdb"):
        from .engines.postgres_diff import PostgresDiff
        return PostgresDiff().diff(before, after)

    if normalized in ("mysql", "mariadb"):
        from .engines.mysql_diff import MySQLDiff
        return MySQLDiff().diff(before, after)

    if normalized == "mongodb":
        from .engines.mongodb_diff import MongoDBDiff
        return MongoDBDiff().diff(before, after)

    if normalized == "redis":
        from .engines.redis_diff import RedisDiff
        return RedisDiff().diff(before, after)

    raise ValueError(
        f"No schema differ available for engine '{engine}'. "
        f"Supported: postgresql, supabase, neon, cockroachdb, mysql, mariadb, mongodb, redis."
    )
