"""Provider check: does Scout catch schema changes on a real Postgres provider?

Connects Scout's Postgres listener to a database, makes four schema changes on a
scratch table, and reports whether each one was caught and how long it took.
Use a throwaway database. It only creates and drops tables named sz_check_*,
and removes the trigger Scout installs when it is done.

    python provider_check.py "postgresql://user:pass@host:5432/db"
    python provider_check.py POOLED_DSN --ddl-dsn DIRECT_DSN     # pooled hosts
    python provider_check.py DSN --wait 90

--ddl-dsn is the connection used to make the changes (default: same as DSN).
Pooled strings (Supabase :6543, Neon -pooler) can't run LISTEN, so Scout polls
every 30s on them. Allow --wait 75 or more.

Exit code 0 if every change was caught, 1 if any was missed.
"""

import argparse
import asyncio
import sys
import time
import uuid
from types import SimpleNamespace

import asyncpg

from scout.listeners.postgres_listener import (
    PostgresListener,
    _parse_connection,
    remove_ddl_trigger,
)


class _Query:
    def __init__(self, store, name):
        self.store, self.name, self.row = store, name, None

    def insert(self, row):
        self.row = {"id": str(uuid.uuid4()), **row}
        return self

    def upsert(self, row, **_):
        self.row = dict(row)
        return self

    def execute(self):
        self.store.setdefault(self.name, []).append(self.row)
        return SimpleNamespace(data=[self.row])


class _Store:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        return _Query(self.tables, name)


async def _run(sql: str, dsn: str):
    cfg = _parse_connection(dsn)
    kwargs = {"statement_cache_size": 0}
    if cfg.ssl_arg is not None:
        kwargs["ssl"] = cfg.ssl_arg
    conn = await asyncpg.connect(cfg.dsn, **kwargs)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


async def check(dsn: str, ddl_dsn: str, wait: int) -> int:
    store = _Store()
    listener = PostgresListener("check-db", "check-org", store)

    async def no_zero(*_):
        pass

    listener.trigger_zero = no_zero

    cfg = _parse_connection(dsn)
    print(f"Provider detected: {cfg.provider}   Pooled connection: {cfg.is_pooler}")

    steps = [
        ("add column", "ALTER TABLE sz_check_a ADD COLUMN c int", "column_added", "c"),
        ("drop column", "ALTER TABLE sz_check_a DROP COLUMN b", "column_dropped", "b"),
        ("create index", "CREATE INDEX sz_check_a_idx ON sz_check_a (a)", "index_created", "sz_check_a_idx"),
        ("drop table", "DROP TABLE sz_check_b", "table_dropped", "sz_check_b"),
    ]

    await _run("DROP TABLE IF EXISTS sz_check_a; DROP TABLE IF EXISTS sz_check_b;", ddl_dsn)
    await _run(
        "CREATE TABLE sz_check_a (id int primary key, a text, b text);"
        "CREATE TABLE sz_check_b (id int primary key)",
        ddl_dsn,
    )

    results = []
    task = None
    try:
        await listener.connect(dsn)
        task = asyncio.create_task(listener.listen())
        await asyncio.sleep(4)
        mode = "event trigger (instant)" if getattr(listener, "_use_notify", False) else "polling (every 30s)"
        print(f"Scout is using: {mode}\n")

        for label, sql, change_type, name in steps:
            seen = len(store.tables.get("change_events", []))
            start = time.time()
            await _run(sql, ddl_dsn)
            took = None
            while time.time() - start < wait:
                new = store.tables.get("change_events", [])[seen:]
                if any(e["change_type"] == change_type and name in e["object_name"] for e in new):
                    took = time.time() - start
                    break
                await asyncio.sleep(0.25)
            results.append((label, took))
            print(f"  {label:13} " + (f"PASS  caught in {took:.1f}s" if took is not None else f"FAIL  not caught within {wait}s"))
    except Exception as exc:
        print(f"\nERROR: could not run the check: {exc}")
        return 1
    finally:
        if task:
            listener._running = False
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        try:
            await listener.disconnect()
        except Exception:
            pass
        try:
            await _run("DROP TABLE IF EXISTS sz_check_a; DROP TABLE IF EXISTS sz_check_b;", ddl_dsn)
            await remove_ddl_trigger(ddl_dsn)
        except Exception as exc:
            print(f"\nCleanup warning: {exc}. Drop sz_check_* tables and the schemazero_ddl_watcher trigger by hand.")

    missed = [r for r in results if r[1] is None]
    print("\nRESULT: " + ("all changes caught" if not missed else f"{len(missed)} of {len(results)} missed"))
    return 1 if missed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Check Scout against a real Postgres provider.")
    ap.add_argument("dsn", help="connection string Scout would use")
    ap.add_argument("--ddl-dsn", help="connection used to make the test changes (default: same as dsn)")
    ap.add_argument("--wait", type=int, default=45, help="seconds to wait for each change (default 45)")
    args = ap.parse_args()
    return asyncio.run(check(args.dsn, args.ddl_dsn or args.dsn, args.wait))


if __name__ == "__main__":
    sys.exit(main())
