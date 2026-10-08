"""Connecting a database: format and host checks, safe errors, encrypted storage,
and keeping passwords out of the chat."""

import base64
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.agent as agent_router
import routers.databases as databases_router
from services import connection_test as ct
from services.encryption_service import EncryptionService
from services.supabase_service import verify_jwt

PASSWORD = "hunter2-very-secret"
PG_URI = f"postgresql://app:{PASSWORD}@db.example.com:5432/prod"


# ---- format and host checks -------------------------------------------------

def test_unsupported_engine_is_rejected():
    with pytest.raises(ct.ConnectionTestError, match="isn't supported"):
        ct.check_format("snowflake", "snowflake://u:p@h/db")


def test_wrong_scheme_is_rejected():
    with pytest.raises(ct.ConnectionTestError, match="doesn't look like a mysql"):
        ct.check_format("mysql", "postgresql://u:p@h/db")


def test_private_and_local_hosts_are_blocked(monkeypatch):
    monkeypatch.delenv("ALLOW_PRIVATE_DB_HOSTS", raising=False)
    for host in ("127.0.0.1", "10.0.0.5", "192.168.1.9", "169.254.169.254"):
        with pytest.raises(ct.ConnectionTestError, match="private network"):
            ct.check_host_allowed(f"postgresql://u:p@{host}:5432/db")


def test_public_host_is_allowed(monkeypatch):
    monkeypatch.delenv("ALLOW_PRIVATE_DB_HOSTS", raising=False)
    ct.check_host_allowed("postgresql://u:p@8.8.8.8:5432/db")


def test_private_hosts_allowed_for_local_dev(monkeypatch):
    monkeypatch.setenv("ALLOW_PRIVATE_DB_HOSTS", "1")
    ct.check_host_allowed("postgresql://u:p@127.0.0.1:5432/db")


# ---- mongodb+srv: the servers the SRV records name must be public too ---------------

class _Srv:
    def __init__(self, target):
        self.target = target


def _fake_srv(monkeypatch, targets):
    import dns.resolver

    monkeypatch.delenv("ALLOW_PRIVATE_DB_HOSTS", raising=False)
    monkeypatch.setattr(dns.resolver, "resolve", lambda *a, **k: [_Srv(t + ".") for t in targets])


def test_srv_pointing_at_a_private_server_is_blocked(monkeypatch):
    _fake_srv(monkeypatch, ["8.8.8.8", "10.0.0.7"])  # one bad target is enough
    with pytest.raises(ct.ConnectionTestError, match="private network"):
        ct.check_host_allowed("mongodb+srv://u:p@cluster.example.net/db")


def test_srv_pointing_at_link_local_metadata_address_is_blocked(monkeypatch):
    _fake_srv(monkeypatch, ["169.254.169.254"])
    with pytest.raises(ct.ConnectionTestError, match="private network"):
        ct.check_host_allowed("mongodb+srv://u:p@cluster.example.net/db")


def test_srv_pointing_at_public_servers_is_allowed(monkeypatch):
    _fake_srv(monkeypatch, ["8.8.8.8", "1.1.1.1"])
    ct.check_host_allowed("mongodb+srv://u:p@cluster.example.net/db")


def test_srv_lookup_failure_is_a_friendly_error(monkeypatch):
    import dns.exception
    import dns.resolver

    monkeypatch.delenv("ALLOW_PRIVATE_DB_HOSTS", raising=False)

    def boom(*a, **k):
        raise dns.exception.DNSException("nope")

    monkeypatch.setattr(dns.resolver, "resolve", boom)
    with pytest.raises(ct.ConnectionTestError, match="Couldn't find that host"):
        ct.check_host_allowed("mongodb+srv://u:p@cluster.example.net/db")


# ---- error messages never leak the password ---------------------------------

def test_error_messages_do_not_contain_secrets():
    import asyncpg

    for exc in (
        asyncpg.InvalidPasswordError(f"password authentication failed for {PASSWORD}"),
        OSError(f"connect failed {PG_URI}"),
        RuntimeError(f"weird {PG_URI}"),
    ):
        text = str(ct._explain(exc))
        assert PASSWORD not in text and "db.example.com" not in text


def test_bad_password_message():
    import asyncpg

    assert "username or password" in str(ct._explain(asyncpg.InvalidPasswordError("x")))


# ---- POST /databases/ -------------------------------------------------------

class FakeService:
    stored: list[dict] = []

    async def create_connected_database(self, org_id, engine, display_name, encrypted_connection_string):
        row = {
            "id": "11111111-1111-1111-1111-111111111111", "org_id": org_id, "engine": engine,
            "display_name": display_name, "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
            "encrypted_connection_string": encrypted_connection_string,
        }
        FakeService.stored.append(row)
        return row


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode())
    FakeService.stored = []
    monkeypatch.setattr(databases_router, "SupabaseService", FakeService)
    monkeypatch.setattr(databases_router, "orgs_with_access", lambda sb, ids: set(ids))
    monkeypatch.setattr(databases_router, "get_supabase", lambda: None)
    app = FastAPI()
    app.include_router(databases_router.router, prefix="/databases")
    app.dependency_overrides[verify_jwt] = lambda: {"org_id": "org-1", "user_id": "u", "email": "e"}
    return TestClient(app)


def _body(**over):
    return {"engine": "postgresql", "display_name": "Prod", "connection_string": PG_URI, **over}


def test_success_stores_encrypted_and_never_returns_the_string(client, monkeypatch):
    async def ok(engine, conn):
        return None

    monkeypatch.setattr(databases_router, "test_connection", ok)
    res = client.post("/databases/", json=_body())
    assert res.status_code == 201
    assert PASSWORD not in res.text and "encrypted_connection_string" not in res.json()
    stored = FakeService.stored[0]
    assert PASSWORD not in stored["encrypted_connection_string"]
    assert EncryptionService().decrypt(stored["encrypted_connection_string"]) == PG_URI


def test_failed_test_stores_nothing_and_returns_safe_message(client, monkeypatch):
    async def fail(engine, conn):
        raise ct.ConnectionTestError("The database refused the username or password.")

    monkeypatch.setattr(databases_router, "test_connection", fail)
    res = client.post("/databases/", json=_body())
    assert res.status_code == 400
    assert "refused" in res.json()["detail"] and PASSWORD not in res.text
    assert FakeService.stored == []


def test_unsupported_engine_returns_400(client):
    res = client.post("/databases/", json=_body(engine="oracle"))
    assert res.status_code == 400 and "isn't supported" in res.json()["detail"]


def test_blank_name_returns_400(client):
    assert client.post("/databases/", json=_body(display_name="  ")).status_code == 400


# ---- chat must never see a password -----------------------------------------

@pytest.fixture
def chat_client(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("Claude was called with a credential-bearing message")

    monkeypatch.setattr(agent_router, "AnthropicService", boom)
    app = FastAPI()
    app.state.agent_prompts = {"obi": "x"}
    app.include_router(agent_router.router, prefix="/agent")
    app.dependency_overrides[verify_jwt] = lambda: {"org_id": "org-1", "user_id": "u", "email": "e"}
    return TestClient(app)


@pytest.mark.parametrize("secret", [
    "postgresql://app:hunter2@db.example.com:5432/prod",
    "mongodb+srv://a:b@cluster.mongodb.net/x",
    "redis://:pw@host:6379",
])
def test_chat_rejects_credentials_in_message(chat_client, secret):
    res = chat_client.post("/agent/chat", json={"agent": "obi", "message": f"here: {secret}"})
    assert res.status_code == 400 and "secure box" in res.json()["detail"]


def test_chat_rejects_credentials_already_in_history(chat_client):
    history = [{"role": "user", "content": PG_URI}]
    res = chat_client.post("/agent/chat", json={"agent": "obi", "message": "hi", "history": history})
    assert res.status_code == 400


def test_expired_trial_cannot_add_a_database(client, monkeypatch):
    monkeypatch.setattr(databases_router, "orgs_with_access", lambda sb, ids: set())
    r = client.post("/databases/", json=_body())
    assert r.status_code == 402
    assert "trial has ended" in r.json()["detail"]
    assert FakeService.stored == []
