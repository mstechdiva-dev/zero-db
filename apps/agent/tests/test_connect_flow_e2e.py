"""Whole path, nothing skipped but Supabase and Claude's reply:

  save a database through POST /databases/  ->  Scout picks it up
  -> a column is dropped  ->  Zero scores it  ->  signed webhook arrives.

Needs a throwaway Postgres: ZERO_TEST_PG_DSN=postgresql://postgres@127.0.0.1:5544/appdb
"""

import asyncio
import base64
import hashlib
import hmac
import json
import os

import asyncpg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.test_pipeline_e2e import AGENTS_DIR, FakeSupabase, PG_DSN, PLAN_ROWS, _webhook_server

pytestmark = pytest.mark.skipif(not PG_DSN, reason="ZERO_TEST_PG_DSN not set")
SECRET = "flow-signing-secret"


@pytest.mark.asyncio
async def test_connect_then_watch_then_alert(monkeypatch):
    import routers.databases as databases_router
    import scout.scout_runner as scout_runner
    import zero.zero_runner as zero_runner
    from scout.listeners.postgres_listener import PostgresListener
    from services.anthropic_service import AnthropicService
    from services.connection_test import test_connection as real_test_connection
    from services.supabase_service import verify_jwt

    monkeypatch.setenv("ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode())
    monkeypatch.setenv("ALLOW_PRIVATE_DB_HOSTS", "1")  # the test database is on localhost
    monkeypatch.setenv("SCHEMAZERO_WEBHOOK_SIGNING_SECRET", SECRET)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    async def canned_chat(self, message, history):
        return json.dumps({"affected_queries": [], "affected_services": [], "affected_indexes": [],
                           "summary": "A column was dropped.", "next_action": "", "recommendations": []})

    monkeypatch.setattr(AnthropicService, "chat", canned_chat)

    received: list = []
    server = _webhook_server(received)
    org_id = "org-1"
    fake = FakeSupabase()
    fake.tables["plans"] = PLAN_ROWS
    fake.tables["organizations"] = [{"id": "org-1", "plan": "solo", "trial_converted": False,
                                     "trial_ends_at": "2030-01-01T00:00:00+00:00"}]
    fake.tables["alert_configs"] = [{"org_id": org_id, "notify_on": ["high", "critical"],
                                     "webhook_url": f"http://127.0.0.1:{server.server_port}/hook",
                                     "email_recipients": []}]

    class Service:
        async def get_connected_databases(self, org_id):
            return []

        async def create_connected_database(self, org_id, engine, display_name, encrypted_connection_string):
            return fake.table("connected_databases").insert({
                "org_id": org_id, "engine": engine, "display_name": display_name,
                "encrypted_connection_string": encrypted_connection_string, "is_active": True,
                "created_at": "2026-01-01T00:00:00Z"}).execute().data[0]

    monkeypatch.setattr(databases_router, "SupabaseService", Service)
    monkeypatch.setattr(databases_router, "test_connection", real_test_connection)
    monkeypatch.setattr(databases_router, "get_supabase", lambda: fake)
    monkeypatch.setattr(scout_runner, "get_supabase", lambda: fake)
    monkeypatch.setattr(zero_runner, "get_supabase", lambda: fake)

    prompts = {f[:-3]: open(os.path.join(AGENTS_DIR, f), encoding="utf-8").read()
               for f in os.listdir(AGENTS_DIR) if f.endswith(".md")}

    async def trigger_zero(self, event_id, internal_url):
        await zero_runner.ZeroRunner(agent_prompts=prompts).analyze(event_id)

    monkeypatch.setattr(PostgresListener, "trigger_zero", trigger_zero)

    admin = await asyncpg.connect(PG_DSN)
    await admin.execute("DROP TABLE IF EXISTS zero_e2e_orders")
    await admin.execute("CREATE TABLE zero_e2e_orders (id serial primary key, note text, legacy_ref text)")

    # 1. Connect through the API, the way the secure form does.
    app = FastAPI()
    app.include_router(databases_router.router, prefix="/databases")
    app.dependency_overrides[verify_jwt] = lambda: {"org_id": org_id, "user_id": "u", "email": "e"}
    res = TestClient(app).post("/databases/", json={
        "engine": "postgresql", "display_name": "Flow test", "connection_string": PG_DSN})
    assert res.status_code == 201, res.text

    # 2. Scout notices the new database.
    runner = scout_runner.ScoutRunner()
    runner._running = True
    try:
        await runner._reconcile()
        assert len(runner._listeners) == 1
        await asyncio.sleep(1.5)  # DDL trigger installs, LISTEN starts

        # 3. Someone drops a column.
        await admin.execute("ALTER TABLE zero_e2e_orders DROP COLUMN legacy_ref")
        for _ in range(100):
            if received:
                break
            await asyncio.sleep(0.1)
        assert received, "no alert arrived after the column was dropped"
    finally:
        await runner.stop()
        await admin.execute("DROP TABLE IF EXISTS zero_e2e_orders")
        await admin.close()
        server.shutdown()

    headers, body = received[0]
    payload = json.loads(body)
    assert payload["object_name"] == "legacy_ref" and payload["risk_level"] == "high"
    ts = headers["SchemaZero-Timestamp"]
    sig = hmac.new(SECRET.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    assert headers["SchemaZero-Signature"] == f"sha256={sig}"
    assert any(r["database_id"] == fake.tables["connected_databases"][0]["id"]
               for r in fake.tables["scout_heartbeat"])


@pytest.mark.asyncio
async def test_real_connection_errors_are_friendly(monkeypatch):
    from services.connection_test import ConnectionTestError, test_connection as real

    monkeypatch.setenv("ALLOW_PRIVATE_DB_HOSTS", "1")
    ok = PG_DSN
    assert await real("postgresql", ok) is None

    missing_db = ok.rsplit("/", 1)[0] + "/no_such_db_zero"
    with pytest.raises(ConnectionTestError, match="database name doesn't exist"):
        await real("postgresql", missing_db)

    with pytest.raises(ConnectionTestError, match="Couldn't reach"):
        await real("postgresql", "postgresql://u:p@127.0.0.1:1/db")
