"""End-to-end check: a real DROP COLUMN flows Scout -> Zero -> signed webhook.

Real: Postgres, the Scout listener (DDL trigger + snapshots + diff), Zero's
risk scoring, the alert dispatcher, and webhook signing.
Faked: Supabase (in-memory) and Claude's reply (canned JSON).

Skipped unless ZERO_TEST_PG_DSN points at a throwaway Postgres superuser
connection, e.g. postgresql://postgres@127.0.0.1:5544/appdb
"""

import asyncio
import hashlib
import hmac
import json
import os
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import asyncpg
import pytest

PG_DSN = os.environ.get("ZERO_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not PG_DSN, reason="ZERO_TEST_PG_DSN not set")

AGENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "agents")
SECRET = "test-signing-secret"


# Real columns and enum values from supabase/schema.sql + migrations, so a
# write the real database would reject fails here too.
COLUMNS = {
    "change_events": {"id", "org_id", "database_id", "change_type", "object_type",
                      "object_name", "schema_name", "before_state", "after_state",
                      "risk_level", "detected_at"},
    "impact_analysis": {"id", "change_event_id", "affected_queries", "affected_services",
                        "affected_indexes", "summary", "next_action", "recommendations",
                        "raw_claude_response", "created_at"},
    "notification_log": {"id", "org_id", "change_event_id", "channel", "status",
                         "error_message", "sent_at"},
    "scout_heartbeat": {"id", "database_id", "last_seen", "created_at"},
    "connected_databases": {"id", "org_id", "engine", "display_name",
                            "encrypted_connection_string", "is_active", "created_at"},
}
ENUMS = {
    ("change_events", "change_type"): {
        "table_added", "table_created", "table_dropped", "column_added", "column_dropped",
        "column_modified", "index_added", "index_created", "index_dropped",
        "constraint_added", "constraint_dropped", "type_changed", "nullable_changed",
        "default_changed", "collection_added", "collection_dropped", "validation_changed",
        "key_pattern_added", "key_pattern_dropped", "key_type_changed", "ttl_changed",
        "ttl_policy_changed", "primary_key_changed", "foreign_key_dropped"},
    ("change_events", "risk_level"): {"low", "medium", "high", "critical"},
    ("notification_log", "channel"): {"webhook", "slack", "pagerduty", "email"},
    ("notification_log", "status"): {"sent", "failed", "skipped"},
    ("connected_databases", "engine"): {
        "postgresql", "supabase", "neon", "cockroachdb", "mysql", "mariadb", "mongodb",
        "redis", "sqlserver", "sqlite", "oracle", "snowflake", "dynamodb"},
}


def _check_write(table: str, row: dict) -> None:
    if table not in COLUMNS:
        return
    unknown = set(row) - COLUMNS[table]
    assert not unknown, f"{table} has no column(s) {sorted(unknown)}"
    for (t, col), allowed in ENUMS.items():
        if t == table and col in row:
            assert row[col] in allowed, f"{table}.{col}={row[col]!r} not in enum"


class FakeSupabase:
    """Just enough of the supabase-py query builder for Scout and Zero."""

    def __init__(self):
        self.tables: dict[str, list[dict]] = {}

    def table(self, name):
        return _Query(self, name)


class _Query:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.rows = db.tables.setdefault(name, [])
        self.mode, self.payload, self.filters, self.one = "select", None, [], False

    def select(self, *a, **k):
        return self

    def insert(self, row):
        self.mode, self.payload = "insert", row
        return self

    def update(self, vals):
        self.mode, self.payload = "update", vals
        return self

    def upsert(self, row, **k):
        self.mode, self.payload = "upsert", row
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def single(self):
        self.one = True
        return self

    def _match(self):
        return [r for r in self.rows if all(r.get(c) == v for c, v in self.filters)]

    def execute(self):
        if self.mode in ("insert", "update", "upsert"):
            _check_write(self.name, self.payload)
        if self.mode == "insert":
            row = {"id": str(uuid.uuid4()), **self.payload}
            self.rows.append(row)
            return SimpleNamespace(data=[row])
        if self.mode == "update":
            for r in self._match():
                r.update(self.payload)
            return SimpleNamespace(data=self._match())
        if self.mode == "upsert":
            self.rows.append(dict(self.payload))
            return SimpleNamespace(data=[self.payload])
        found = self._match()
        if self.one:
            return SimpleNamespace(data=found[0] if found else None)
        return SimpleNamespace(data=found)


def _webhook_server(received: list):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append((dict(self.headers), body))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.mark.asyncio
async def test_column_drop_reaches_signed_webhook(monkeypatch):
    from scout.listeners.postgres_listener import PostgresListener
    from services.anthropic_service import AnthropicService
    import zero.zero_runner as zero_runner

    monkeypatch.setenv("SCHEMAZERO_WEBHOOK_SIGNING_SECRET", SECRET)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    async def canned_chat(self, message, history):
        return json.dumps(
            {
                "affected_queries": ["SELECT legacy_email FROM zero_e2e_users"],
                "affected_services": [],
                "affected_indexes": [],
                "summary": "legacy_email was dropped from zero_e2e_users.",
                "next_action": "",
                "recommendations": ["Check code that still reads legacy_email."],
            }
        )

    monkeypatch.setattr(AnthropicService, "chat", canned_chat)

    received: list = []
    server = _webhook_server(received)
    org_id, db_id = "org-1", "db-1"

    fake = FakeSupabase()
    fake.tables["alert_configs"] = [
        {
            "org_id": org_id,
            "notify_on": ["high", "critical"],
            "webhook_url": f"http://127.0.0.1:{server.server_port}/hook",
            "email_recipients": [],
        }
    ]
    fake.tables["connected_databases"] = [
        {"id": db_id, "org_id": org_id, "display_name": "test-postgres"}
    ]
    monkeypatch.setattr(zero_runner, "get_supabase", lambda: fake)

    prompts = {
        f[:-3]: open(os.path.join(AGENTS_DIR, f), encoding="utf-8").read()
        for f in os.listdir(AGENTS_DIR)
        if f.endswith(".md")
    }
    assert "zero" in prompts, "agents/zero.md must be loadable"

    admin = await asyncpg.connect(PG_DSN)
    await admin.execute("DROP TABLE IF EXISTS zero_e2e_users")
    await admin.execute("CREATE TABLE zero_e2e_users (id serial primary key, email text, legacy_email text)")

    listener = PostgresListener(database_id=db_id, org_id=org_id, supabase_client=fake)

    async def trigger_zero(event_id, internal_url):
        await zero_runner.ZeroRunner(agent_prompts=prompts).analyze(event_id)

    listener.trigger_zero = trigger_zero
    await listener.connect(PG_DSN)
    task = asyncio.create_task(listener.listen())
    try:
        await asyncio.sleep(1.5)  # let the DDL trigger install and LISTEN start
        await admin.execute("ALTER TABLE zero_e2e_users DROP COLUMN legacy_email")

        for _ in range(100):
            if received:
                break
            await asyncio.sleep(0.1)
        assert received, "no webhook arrived after the column was dropped"
    finally:
        listener._running = False
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await listener.disconnect()
        await admin.execute("DROP TABLE IF EXISTS zero_e2e_users")
        await admin.close()
        server.shutdown()

    event = next(
        e for e in fake.tables["change_events"] if e["change_type"] == "column_dropped"
    )
    assert event["object_name"] == "legacy_email"
    assert event["risk_level"] == "high"
    assert fake.tables["impact_analysis"][0]["change_event_id"] == event["id"]

    headers, body = received[0]
    payload = json.loads(body)
    assert payload["risk_level"] == "high"
    assert payload["object_name"] == "legacy_email"
    ts = headers["SchemaZero-Timestamp"]
    expected = hmac.new(SECRET.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    assert headers["SchemaZero-Signature"] == f"sha256={expected}"

    logged = [r for r in fake.tables.get("notification_log", []) if r.get("channel") == "webhook"]
    assert logged and logged[0]["status"] == "sent"
    assert any(r["database_id"] == db_id for r in fake.tables.get("scout_heartbeat", []))
