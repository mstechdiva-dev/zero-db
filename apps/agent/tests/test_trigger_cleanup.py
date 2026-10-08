"""Disconnecting a Postgres database takes SchemaZero's trigger back out.

Skipped unless ZERO_TEST_PG_DSN points at a throwaway Postgres superuser connection.
"""

import os

import asyncpg
import pytest

from scout.listeners.postgres_listener import (
    NOTIFY_FUNCTION_SQL,
    remove_ddl_trigger,
)

PG_DSN = os.environ.get("ZERO_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not PG_DSN, reason="ZERO_TEST_PG_DSN not set")


async def _trigger_exists(conn) -> bool:
    return bool(await conn.fetchval(
        "select 1 from pg_event_trigger where evtname = 'schemazero_ddl_watcher'"))


@pytest.mark.asyncio
async def test_remove_ddl_trigger_drops_trigger_and_function():
    conn = await asyncpg.connect(PG_DSN)
    try:
        await conn.execute(NOTIFY_FUNCTION_SQL)
        assert await _trigger_exists(conn)

        assert await remove_ddl_trigger(PG_DSN) is True

        assert not await _trigger_exists(conn)
        assert not await conn.fetchval(
            "select 1 from pg_proc where proname = 'schemazero_notify_ddl'")
        # Running it again when nothing is installed is fine.
        assert await remove_ddl_trigger(PG_DSN) is True
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_remove_ddl_trigger_returns_false_when_unreachable():
    assert await remove_ddl_trigger("postgresql://u:p@127.0.0.1:1/db") is False
