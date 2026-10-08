"""Check that a database connection string works before we store it.

Used by POST /databases/. Errors are returned as ConnectionTestError with a
message that is safe to show the user: it never includes the connection
string, the password, or the driver's raw error text.
"""

import asyncio
import ipaddress
import os
import socket
import ssl
from urllib.parse import urlparse

TIMEOUT = 10  # seconds

# Engines Scout has a listener for.
SUPPORTED_ENGINES = {
    "postgresql", "supabase", "neon", "cockroachdb",
    "mysql", "mariadb", "mongodb", "redis",
}
POSTGRES_FAMILY = {"postgresql", "supabase", "neon", "cockroachdb"}

SCHEMES = {
    "postgresql": ("postgresql", "postgres"),
    "supabase": ("postgresql", "postgres"),
    "neon": ("postgresql", "postgres"),
    "cockroachdb": ("postgresql", "postgres"),
    "mysql": ("mysql",),
    "mariadb": ("mysql", "mariadb"),
    "mongodb": ("mongodb", "mongodb+srv"),
    "redis": ("redis", "rediss"),
}


class ConnectionTestError(Exception):
    """Raised with a message that is safe to show to the user."""


def check_format(engine: str, connection_string: str) -> None:
    if engine not in SUPPORTED_ENGINES:
        raise ConnectionTestError(f"{engine} isn't supported yet.")
    parsed = urlparse(connection_string.strip())
    if parsed.scheme not in SCHEMES[engine] or not parsed.hostname:
        expected = " or ".join(f"{s}://" for s in SCHEMES[engine])
        raise ConnectionTestError(
            f"That doesn't look like a {engine} connection string. It should start with {expected}"
        )


def check_host_allowed(connection_string: str) -> None:
    """Refuse hosts on private or local networks, so this endpoint can't be
    used to probe the servers SchemaZero itself runs next to.

    Set ALLOW_PRIVATE_DB_HOSTS=1 for local development and tests only.
    mongodb+srv hosts are looked up through DNS SRV records, which this check
    can't see, so they are not checked here.
    """
    if os.environ.get("ALLOW_PRIVATE_DB_HOSTS") == "1":
        return
    parsed = urlparse(connection_string.strip())
    if parsed.scheme.endswith("+srv"):
        return
    host = parsed.hostname or ""
    try:
        infos = socket.getaddrinfo(host, parsed.port or 0, type=socket.SOCK_STREAM)
    except OSError:
        raise ConnectionTestError("Couldn't find that host. Check the address in your connection string.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ConnectionTestError(
                "That address is on a private network, so SchemaZero can't reach it. "
                "Use your database's public address."
            )


def _explain(exc: Exception) -> ConnectionTestError:
    name = type(exc).__name__
    if name in ("InvalidPasswordError", "InvalidAuthorizationSpecificationError") or "Access denied" in str(exc) or name == "AuthenticationFailed" or name == "AuthenticationError":
        return ConnectionTestError("The database refused the username or password.")
    if name == "InvalidCatalogNameError":
        return ConnectionTestError("The host answered, but that database name doesn't exist.")
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)) or "Timeout" in name:
        return ConnectionTestError(
            "Timed out. Check the host and port, and that the database allows connections from outside its network."
        )
    if isinstance(exc, ssl.SSLError) or "SSL" in name:
        return ConnectionTestError("The SSL handshake failed. Try adding ?sslmode=require to the connection string.")
    if isinstance(exc, (OSError, ConnectionError)) or "Connection" in name:
        return ConnectionTestError(
            "Couldn't reach the database. Check the host and port, and that it allows outside connections."
        )
    return ConnectionTestError(f"Couldn't connect ({name}). Check the connection string.")


async def _test_postgres(connection_string: str) -> None:
    import asyncpg
    from scout.listeners.postgres_listener import _parse_connection

    cfg = _parse_connection(connection_string.strip())
    kwargs: dict = {"timeout": TIMEOUT}
    if cfg.ssl_arg is not None:
        kwargs["ssl"] = cfg.ssl_arg
    if cfg.is_pooler:
        kwargs["statement_cache_size"] = 0
    conn = await asyncpg.connect(cfg.dsn, **kwargs)
    try:
        await conn.fetchval("SELECT 1")
    finally:
        await conn.close()


async def _test_mysql(connection_string: str) -> None:
    import aiomysql

    parsed = urlparse(connection_string.strip())
    conn = await aiomysql.connect(
        host=parsed.hostname,
        port=parsed.port or 3306,
        user=parsed.username or "root",
        password=parsed.password or "",
        db=parsed.path.lstrip("/") or None,
        connect_timeout=TIMEOUT,
    )
    conn.close()


async def _test_mongodb(connection_string: str) -> None:
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(connection_string.strip(), serverSelectionTimeoutMS=TIMEOUT * 1000)
    try:
        await client.admin.command("ping")
    finally:
        client.close()


async def _test_redis(connection_string: str) -> None:
    import redis.asyncio as aioredis

    client = aioredis.from_url(connection_string.strip(), socket_connect_timeout=TIMEOUT)
    try:
        await client.ping()
    finally:
        await client.aclose()


async def test_connection(engine: str, connection_string: str) -> None:
    """Raise ConnectionTestError (safe message) if the database can't be reached."""
    check_format(engine, connection_string)
    check_host_allowed(connection_string)
    tester = (
        _test_postgres if engine in POSTGRES_FAMILY
        else _test_mysql if engine in ("mysql", "mariadb")
        else _test_mongodb if engine == "mongodb"
        else _test_redis
    )
    try:
        await asyncio.wait_for(tester(connection_string), timeout=TIMEOUT + 5)
    except ConnectionTestError:
        raise
    except Exception as exc:
        raise _explain(exc) from None
