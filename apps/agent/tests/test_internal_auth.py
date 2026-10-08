"""/internal/analyze must not be open to the public when no secret is set."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.internal as internal


class _StubRunner:
    def __init__(self, agent_prompts):
        pass

    async def analyze(self, change_event_id):
        return {"ok": True}


@pytest.fixture
def client(monkeypatch):
    import zero.zero_runner as zero_runner

    monkeypatch.setattr(zero_runner, "ZeroRunner", _StubRunner)
    app = FastAPI()
    app.state.agent_prompts = {}
    app.include_router(internal.router, prefix="/internal")
    return TestClient(app)


def _post(client, headers=None):
    return client.post("/internal/analyze", json={"change_event_id": "e1"}, headers=headers or {})


def test_no_secret_rejects_non_local_callers(client, monkeypatch):
    monkeypatch.setattr(internal, "INTERNAL_SECRET", "")
    assert _post(client).status_code == 403  # TestClient is not 127.0.0.1


def test_no_secret_allows_loopback(monkeypatch):
    monkeypatch.setattr(internal, "INTERNAL_SECRET", "")
    app = FastAPI()
    app.state.agent_prompts = {}
    app.include_router(internal.router, prefix="/internal")
    import zero.zero_runner as zero_runner
    monkeypatch.setattr(zero_runner, "ZeroRunner", _StubRunner)
    c = TestClient(app, client=("127.0.0.1", 50000))
    assert _post(c).status_code == 200


def test_secret_required_when_set(client, monkeypatch):
    monkeypatch.setattr(internal, "INTERNAL_SECRET", "s3cret")
    assert _post(client).status_code == 403
    assert _post(client, {"X-Internal-Secret": "wrong"}).status_code == 403
    assert _post(client, {"X-Internal-Secret": "s3cret"}).status_code == 200
