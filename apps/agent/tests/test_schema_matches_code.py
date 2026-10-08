"""supabase/schema.sql must match what the code reads and writes.

Runs against a real Postgres (set ZERO_TEST_PG_DSN to a throwaway superuser
connection). It creates and drops its own scratch databases, and stands in for
Supabase's `auth` schema, roles and realtime publication.

  1. The backend's own code runs end to end against the real tables
     (connect -> Scout -> drop a column -> Zero -> signed alert).
  2. Every column the website and backend ask for in a .select(...) exists.
  3. Every change type, engine and alert channel the code can produce is accepted.
  4. Who can see and change what (row-level security and column limits).
  5. Alert settings can be saved twice, signup creates an org, reset.sql keeps
     the waitlist, and existing logins are backfilled.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import asyncpg
import psycopg2
import psycopg2.extras
import pytest
import pytest_asyncio

from tests.test_pipeline_e2e import AGENTS_DIR, PG_DSN, _webhook_server

pytestmark = pytest.mark.skipif(not PG_DSN, reason="ZERO_TEST_PG_DSN not set")

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
RESET = (ROOT / "supabase" / "reset.sql").read_text(encoding="utf-8")

SUPABASE_STANDIN = """
create schema if not exists auth;
create table if not exists auth.users (
  id uuid primary key default gen_random_uuid(), email text, raw_user_meta_data jsonb);
create or replace function auth.uid() returns uuid language sql stable as $$
  select nullif(coalesce(current_setting('request.jwt.claim.sub', true),
         (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')), '')::uuid $$;
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then create role service_role nologin bypassrls; end if;
end $$;
grant usage on schema public, auth to anon, authenticated, service_role;
grant select on auth.users to anon, authenticated, service_role;
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public grant all on sequences to anon, authenticated, service_role;
do $$ begin
  if not exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    create publication supabase_realtime; end if;
end $$;
"""


def _dsn(db: str) -> str:
    p = urlparse(PG_DSN)
    return urlunparse(p._replace(path="/" + db))


async def _fresh_db(name: str, apply_schema: bool = True) -> str:
    admin = await asyncpg.connect(_dsn("postgres"))
    await admin.execute(f'drop database if exists "{name}" with (force)')
    await admin.execute(f'create database "{name}"')
    await admin.close()
    conn = await asyncpg.connect(_dsn(name))
    await conn.execute(SUPABASE_STANDIN)
    if apply_schema:
        await conn.execute(SCHEMA)
    await conn.close()
    return _dsn(name)


async def _drop_db(name: str) -> None:
    admin = await asyncpg.connect(_dsn("postgres"))
    await admin.execute(f'drop database if exists "{name}" with (force)')
    await admin.close()


@pytest_asyncio.fixture
async def db():
    dsn = await _fresh_db("zero_schema_main")
    conn = await asyncpg.connect(dsn)
    yield conn, dsn
    await conn.close()
    await _drop_db("zero_schema_main")


async def _signup(conn, email: str) -> tuple[str, str]:
    """Insert a login the way Supabase does; the trigger makes the org."""
    uid = str(uuid.uuid4())
    await conn.execute("insert into auth.users (id, email) values ($1, $2)", uuid.UUID(uid), email)
    org = await conn.fetchval("select org_id from users where auth_user_id = $1", uuid.UUID(uid))
    return uid, str(org)


async def _as_user(conn, uid: str):
    """Run following statements as that signed-in user (inside a transaction)."""
    await conn.execute("set local role authenticated")
    await conn.execute("select set_config('request.jwt.claims', $1, true)", json.dumps({"sub": uid}))


def _count(status: str) -> int:
    return int(status.split()[-1])


# ---- 1. the backend's own code against the real tables -------------------------

class PgSupabase:
    """The slice of the supabase-py API the backend uses, run on real Postgres."""

    def __init__(self, dsn):
        self.conn = psycopg2.connect(dsn)
        self.conn.autocommit = True

    def table(self, name):
        return _PgQuery(self, name)


class _PgQuery:
    def __init__(self, sb, name):
        self.sb, self.name, self.mode, self.payload = sb, name, "select", None
        self.cols, self.filters, self.one, self.conflict = "*", [], False, None

    def select(self, cols="*", **k):
        self.cols = cols
        return self

    def insert(self, row):
        self.mode, self.payload = "insert", row
        return self

    def update(self, row):
        self.mode, self.payload = "update", row
        return self

    def upsert(self, row, on_conflict=None, **k):
        self.mode, self.payload, self.conflict = "upsert", row, on_conflict
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def single(self):
        self.one = True
        return self

    def _vals(self, d):
        return {k: (psycopg2.extras.Json(v) if isinstance(v, (dict, list)) else v) for k, v in d.items()}

    def execute(self):
        from types import SimpleNamespace
        cur = self.sb.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        where, args = "", []
        if self.filters:
            where = " where " + " and ".join(f'"{c}" = %s' for c, _ in self.filters)
            args = [v for _, v in self.filters]
        t = f'public."{self.name}"'
        if self.mode == "insert":
            d = self._vals(self.payload)
            cur.execute(f'insert into {t} ({",".join(chr(34)+k+chr(34) for k in d)}) values ({",".join(["%s"]*len(d))}) returning *', list(d.values()))
        elif self.mode == "upsert":
            d = self._vals(self.payload)
            target = self.conflict or "id"  # supabase-py defaults to the primary key
            sets = ",".join(f'"{k}" = excluded."{k}"' for k in d if k != target)
            cur.execute(f'insert into {t} ({",".join(chr(34)+k+chr(34) for k in d)}) values ({",".join(["%s"]*len(d))}) '
                        f'on conflict ("{target}") do update set {sets} returning *', list(d.values()))
        elif self.mode == "update":
            d = self._vals(self.payload)
            cur.execute(f'update {t} set {",".join(chr(34)+k+chr(34)+" = %s" for k in d)}{where} returning *', list(d.values()) + args)
        else:
            cur.execute(f"select {self.cols} from {t}{where}", args)
        rows = [{k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in r.items()} for r in cur.fetchall()]
        if self.one:
            return SimpleNamespace(data=rows[0] if rows else None)
        return SimpleNamespace(data=rows)


@pytest.mark.asyncio
async def test_backend_code_works_against_the_real_schema(db, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import routers.databases as databases_router
    import scout.scout_runner as scout_runner
    import services.supabase_service as supabase_service
    import zero.zero_runner as zero_runner
    from scout.listeners.postgres_listener import PostgresListener
    from services.anthropic_service import AnthropicService
    from services.supabase_service import verify_jwt

    conn, dsn = db
    uid, org_id = await _signup(conn, "owner@example.com")
    pg = PgSupabase(dsn)

    monkeypatch.setenv("ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode())
    monkeypatch.setenv("ALLOW_PRIVATE_DB_HOSTS", "1")
    monkeypatch.setenv("SCHEMAZERO_WEBHOOK_SIGNING_SECRET", "s3cret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")

    async def canned_chat(self, message, history):
        return json.dumps({"affected_queries": ["q"], "affected_services": [], "affected_indexes": [],
                           "summary": "A column was dropped.", "next_action": "x", "recommendations": ["r"]})

    monkeypatch.setattr(AnthropicService, "chat", canned_chat)
    for mod in (scout_runner, zero_runner, supabase_service):
        monkeypatch.setattr(mod, "get_supabase", lambda: pg)

    received: list = []
    server = _webhook_server(received)

    # Saving alert settings twice, the way the backend does (needs on_conflict="org_id").
    svc = supabase_service.SupabaseService()
    from models.alert import UpdateAlertConfigRequest
    await svc.update_alert_config(org_id, UpdateAlertConfigRequest(slack_webhook_url="https://hooks.example/1"))
    await svc.update_alert_config(org_id, UpdateAlertConfigRequest(notify_on=["high", "critical"]))
    pg.table("alert_configs").update({"webhook_url": f"http://127.0.0.1:{server.server_port}/hook"}).eq("org_id", org_id).execute()
    assert await conn.fetchval("select count(*) from alert_configs where org_id = $1", uuid.UUID(org_id)) == 1

    # Customer database to watch (same server, another database).
    customer = await _fresh_db("zero_schema_customer", apply_schema=False)
    cust = await asyncpg.connect(customer)
    await cust.execute("create table orders (id serial primary key, note text, legacy_ref text)")

    prompts = {f[:-3]: open(os.path.join(AGENTS_DIR, f), encoding="utf-8").read()
               for f in os.listdir(AGENTS_DIR) if f.endswith(".md")}

    async def trigger_zero(self, event_id, internal_url):
        await zero_runner.ZeroRunner(agent_prompts=prompts).analyze(event_id)

    monkeypatch.setattr(PostgresListener, "trigger_zero", trigger_zero)

    app = FastAPI()
    app.include_router(databases_router.router, prefix="/databases")
    app.dependency_overrides[verify_jwt] = lambda: {"org_id": org_id, "user_id": uid, "email": "owner@example.com"}
    res = TestClient(app).post("/databases/", json={"engine": "postgresql", "display_name": "Customer", "connection_string": customer})
    assert res.status_code == 201, res.text

    runner = scout_runner.ScoutRunner()
    runner._running = True
    try:
        await runner._reconcile()
        assert len(runner._listeners) == 1
        await asyncio.sleep(1.5)
        await cust.execute("ALTER TABLE orders DROP COLUMN legacy_ref")
        for _ in range(100):
            if received:
                break
            await asyncio.sleep(0.1)
        assert received, "no alert arrived"
    finally:
        await runner.stop()
        await cust.close()
        server.shutdown()
        await _drop_db("zero_schema_customer")

    ev = await conn.fetchrow("select * from change_events where org_id = $1", uuid.UUID(org_id))
    assert ev["change_type"] == "column_dropped" and ev["object_name"] == "legacy_ref" and ev["risk_level"] == "high"
    assert await conn.fetchval("select count(*) from impact_analysis where change_event_id = $1", ev["id"]) == 1
    assert await conn.fetchval("select next_action from impact_analysis where change_event_id = $1", ev["id"])
    assert await conn.fetchval("select status::text from notification_log where channel = 'webhook'") == "sent"
    assert await conn.fetchval("select count(*) from scout_heartbeat") >= 1
    headers, body = received[0]
    sig = hmac.new(b"s3cret", f"{headers['SchemaZero-Timestamp']}.".encode() + body, hashlib.sha256).hexdigest()
    assert headers["SchemaZero-Signature"] == f"sha256={sig}"
    stored = await conn.fetchval("select encrypted_connection_string from connected_databases")
    assert customer not in stored


# ---- 2. every column the code selects exists ------------------------------------

SELECT_RE = re.compile(r"""\.(?:from|table)\(\s*["'](\w+)["']\s*\)\s*\.select\(\s*["']([^"']+)["']""", re.S)


def _code_selects():
    found = []
    for base, exts in ((ROOT / "apps" / "web", (".ts", ".tsx")), (ROOT / "apps" / "agent", (".py",))):
        for path in base.rglob("*"):
            parts = set(path.parts)
            if path.suffix not in exts or parts & {"node_modules", ".next", "tests", "__pycache__"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for m in SELECT_RE.finditer(text):
                found.append((str(path.relative_to(ROOT)), m.group(1), m.group(2)))
    return found


@pytest.mark.asyncio
async def test_every_selected_column_exists(db):
    conn, _ = db
    schema_cols = {}
    for r in await conn.fetch("select table_name, column_name from information_schema.columns where table_schema = 'public'"):
        schema_cols.setdefault(r["table_name"], set()).add(r["column_name"])
    selects = _code_selects()
    assert len(selects) >= 15, "the scan found suspiciously few queries"
    problems = []
    for file, table, cols in selects:
        if table not in schema_cols:
            problems.append(f"{file}: no table {table}")
            continue
        for col in (c.strip() for c in cols.split(",")):
            if col and col != "*" and col not in schema_cols[table]:
                problems.append(f"{file}: {table}.{col} does not exist")
    assert not problems, "\n".join(problems)


# ---- 3. every value the code can produce is accepted ----------------------------

def _literals(pattern: str, *dirs: str) -> set[str]:
    out = set()
    for d in dirs:
        for path in (ROOT / "apps" / "agent" / d).rglob("*.py"):
            out |= set(re.findall(pattern, path.read_text(encoding="utf-8")))
    return out


@pytest.mark.asyncio
async def test_every_value_the_code_produces_is_accepted(db):
    conn, _ = db
    import scout.scout_runner as scout_runner
    from services.connection_test import SUPPORTED_ENGINES
    from zero import risk_scorer

    def enum(name):
        return conn.fetch("select e.enumlabel from pg_enum e join pg_type t on t.oid = e.enumtypid where t.typname = $1", name)

    change_types = {r["enumlabel"] for r in await enum("change_type")}
    emitted = _literals(r'"change_type":\s*"([a-z_]+)"', "scout") | _literals(r'change_type="([a-z_]+)"', "scout")
    scored = set().union(risk_scorer.CRITICAL_CHANGE_TYPES, risk_scorer.HIGH_CHANGE_TYPES,
                         risk_scorer.MEDIUM_CHANGE_TYPES, risk_scorer.LOW_CHANGE_TYPES)
    assert len(emitted) >= 10
    assert emitted <= change_types, f"change types Scout writes that the database rejects: {sorted(emitted - change_types)}"
    assert scored <= change_types, f"change types the scorer knows that the database rejects: {sorted(scored - change_types)}"

    engines = {r["enumlabel"] for r in await enum("db_engine")}
    assert set(scout_runner.LISTENER_CLASSES) <= engines and SUPPORTED_ENGINES <= engines

    channels = {r["enumlabel"] for r in await enum("alert_channel")}
    used = _literals(r'_log\(org_id, event_id, "([a-z]+)"', "zero")
    assert used and used <= channels, f"alert channels the code logs that the database rejects: {sorted(used - channels)}"
    assert {r["enumlabel"] for r in await enum("notification_status")} >= {"sent", "failed"}
    assert {r["enumlabel"] for r in await enum("risk_level")} == {"low", "medium", "high", "critical"}


# ---- 4. who can see and change what ---------------------------------------------

async def _two_orgs(conn):
    ua, oa = await _signup(conn, "a@example.com")
    ub, ob = await _signup(conn, "b@example.com")
    ids = {}
    for key, org in (("a", oa), ("b", ob)):
        ids[key] = await conn.fetchval(
            "insert into connected_databases (org_id, engine, display_name, encrypted_connection_string) "
            "values ($1, 'postgresql', $2, 'ENCRYPTED') returning id", uuid.UUID(org), f"db-{key}")
        ev = await conn.fetchval(
            "insert into change_events (org_id, database_id, change_type, object_type, object_name) "
            "values ($1, $2, 'column_dropped', 'column', 'x') returning id", uuid.UUID(org), ids[key])
        await conn.execute("insert into impact_analysis (change_event_id, summary) values ($1, 's')", ev)
        await conn.execute("insert into scout_heartbeat (database_id) values ($1)", ids[key])
    return ua, oa, ub, ob, ids


@pytest.mark.asyncio
async def test_people_only_see_their_own_org(db):
    conn, _ = db
    ua, oa, ub, ob, ids = await _two_orgs(conn)
    async with conn.transaction():
        await _as_user(conn, ua)
        for table in ("organizations", "users", "connected_databases", "change_events", "alert_configs", "scout_heartbeat"):
            n = await conn.fetchval(f"select count(*) from {table}" if table != "connected_databases"
                                    else "select count(id) from connected_databases")
            assert n == 1, f"{table}: user A sees {n} rows"
        assert await conn.fetchval("select count(*) from impact_analysis") == 1
        names = await conn.fetch("select display_name from connected_databases")
        assert [r["display_name"] for r in names] == ["db-a"]


@pytest.mark.asyncio
async def test_connection_strings_are_never_readable_by_users(db):
    conn, _ = db
    ua, *_ = await _two_orgs(conn)
    for sql in ("select encrypted_connection_string from connected_databases", "select * from connected_databases"):
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            async with conn.transaction():
                await _as_user(conn, ua)
                await conn.fetch(sql)
    async with conn.transaction():
        await _as_user(conn, ua)  # the columns the dashboard asks for still work
        assert len(await conn.fetch("select id, engine, display_name, is_active, created_at from connected_databases")) == 1


@pytest.mark.asyncio
async def test_pause_and_delete_work_for_own_databases_only(db):
    conn, _ = db
    ua, oa, ub, ob, ids = await _two_orgs(conn)
    async with conn.transaction():
        await _as_user(conn, ua)
        assert _count(await conn.execute("update connected_databases set is_active = false where id = $1", ids["a"])) == 1
        assert _count(await conn.execute("update connected_databases set is_active = false where id = $1", ids["b"])) == 0
        assert _count(await conn.execute("update connected_databases set display_name = 'renamed' where id = $1", ids["a"])) == 1
        assert _count(await conn.execute("delete from connected_databases where id = $1", ids["b"])) == 0
    assert await conn.fetchval("select is_active from connected_databases where id = $1", ids["a"]) is False
    assert await conn.fetchval("select is_active from connected_databases where id = $1", ids["b"]) is True
    async with conn.transaction():
        await _as_user(conn, ua)
        assert _count(await conn.execute("delete from connected_databases where id = $1", ids["a"])) == 1
    assert await conn.fetchval("select count(*) from change_events where database_id = $1", ids["a"]) == 0  # cascades


@pytest.mark.asyncio
async def test_users_cannot_tamper_with_connections_or_add_their_own(db):
    conn, _ = db
    ua, oa, ub, ob, ids = await _two_orgs(conn)
    for sql, args in (
        ("update connected_databases set encrypted_connection_string = 'x' where id = $1", (ids["a"],)),
        ("update connected_databases set org_id = $2 where id = $1", (ids["a"], uuid.UUID(ob))),
        ("insert into connected_databases (org_id, engine, display_name, encrypted_connection_string) values ($1, 'postgresql', 'x', 'y')", (uuid.UUID(oa),)),
    ):
        with pytest.raises((asyncpg.InsufficientPrivilegeError, asyncpg.exceptions.PostgresError)):
            async with conn.transaction():
                await _as_user(conn, ua)
                await conn.execute(sql, *args)


@pytest.mark.asyncio
async def test_admin_only_tables_are_closed_to_users(db):
    conn, _ = db
    ua, *_ = await _two_orgs(conn)
    await conn.execute("insert into leads (user_email) values ('x@example.com')")
    await conn.execute("insert into agent_skills (name, content) values ('obi', 'c')")
    await conn.execute("insert into waitlist (email) values ('w@example.com')")
    async with conn.transaction():
        await _as_user(conn, ua)
        for table in ("leads", "agent_skills", "waitlist"):
            assert await conn.fetchval(f"select count(*) from {table}") == 0, f"{table} is visible to users"
    with pytest.raises(asyncpg.PostgresError):
        async with conn.transaction():
            await _as_user(conn, ua)
            await conn.execute("insert into waitlist (email) values ('mine@example.com')")


@pytest.mark.asyncio
async def test_settings_save_works_as_the_signed_in_user(db):
    """The website saves alert settings with an upsert on org_id, as the user."""
    conn, _ = db
    ua, oa, ub, ob, ids = await _two_orgs(conn)
    sql = ("insert into alert_configs (org_id, slack_webhook_url, email_recipients, notify_on) "
           "values ($1, $2, $3::jsonb, $4::jsonb) on conflict (org_id) do update set "
           "slack_webhook_url = excluded.slack_webhook_url, email_recipients = excluded.email_recipients, notify_on = excluded.notify_on")
    for hook in ("https://hooks.example/a", "https://hooks.example/b"):
        async with conn.transaction():
            await _as_user(conn, ua)
            await conn.execute(sql, uuid.UUID(oa), hook, '["a@x.com"]', '["high"]')
    assert await conn.fetchval("select slack_webhook_url from alert_configs where org_id = $1", uuid.UUID(oa)) == "https://hooks.example/b"
    with pytest.raises(asyncpg.PostgresError):  # not someone else's org
        async with conn.transaction():
            await _as_user(conn, ua)
            await conn.execute(sql, uuid.UUID(ob), "https://evil.example", "[]", "[]")
    # Without on_conflict the same save is a duplicate-key error. That is why the code names org_id.
    with pytest.raises(asyncpg.UniqueViolationError):
        await conn.execute("insert into alert_configs (org_id) values ($1) on conflict (id) do nothing", uuid.UUID(oa))


# ---- 5. signup, live updates, reset, backfill -----------------------------------

@pytest.mark.asyncio
async def test_signup_creates_org_user_and_alert_settings(db):
    conn, _ = db
    uid, org = await _signup(conn, "new@example.com")
    assert await conn.fetchval("select role::text from users where auth_user_id = $1", uuid.UUID(uid)) == "owner"
    assert await conn.fetchval("select plan::text from organizations where id = $1", uuid.UUID(org)) == "trial"
    assert await conn.fetchval("select count(*) from alert_configs where org_id = $1", uuid.UUID(org)) == 1


@pytest.mark.asyncio
async def test_change_feed_has_live_updates(db):
    conn, _ = db
    assert await conn.fetchval("select count(*) from pg_publication_tables where pubname = 'supabase_realtime' and tablename = 'change_events'") == 1


@pytest.mark.asyncio
async def test_reset_keeps_waitlist_leads_and_prompts_and_backfills_logins(db):
    conn, dsn = db
    uid, org = await _signup(conn, "keep@example.com")
    await conn.execute("insert into waitlist (email) values ('w@example.com')")
    await conn.execute("insert into leads (user_email) values ('l@example.com')")
    await conn.execute("insert into agent_skills (name, content) values ('obi', 'mine')")
    await conn.execute(RESET)
    assert await conn.fetchval("select to_regclass('public.organizations')") is None
    assert await conn.fetchval("select count(*) from waitlist") == 1
    assert await conn.fetchval("select count(*) from leads") == 1
    assert await conn.fetchval("select content from agent_skills") == "mine"
    await conn.execute(SCHEMA)  # rebuilds everything, and gives the existing login an org again
    assert await conn.fetchval("select count(*) from users where auth_user_id = $1", uuid.UUID(uid)) == 1
    assert await conn.fetchval("select count(*) from alert_configs") == 1
    assert await conn.fetchval("select count(*) from waitlist") == 1
    await _signup(conn, "after@example.com")  # the signup trigger is back
    assert await conn.fetchval("select count(*) from users") == 2
