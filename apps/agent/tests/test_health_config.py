"""/health stays up when settings are missing and says which ones; Scout stays off."""

import base64

from fastapi.testclient import TestClient

import config_check

GOOD_KEY = base64.b64encode(b"k" * 32).decode()
ALL = {
    "NEXT_PUBLIC_SUPABASE_URL": "http://x",
    "SUPABASE_SERVICE_ROLE_KEY": "svc",
    "ANTHROPIC_API_KEY": "key",
    "ENCRYPTION_KEY": GOOD_KEY,
}


def _set(monkeypatch, **over):
    for k in config_check.REQUIRED:
        monkeypatch.delenv(k, raising=False)
    for k, v in {**ALL, **over}.items():
        if v is not None:
            monkeypatch.setenv(k, v)


def test_problems_names_missing_and_bad_key(monkeypatch):
    _set(monkeypatch, ENCRYPTION_KEY=None, ANTHROPIC_API_KEY=None)
    assert set(config_check.problems()) == {"ENCRYPTION_KEY", "ANTHROPIC_API_KEY"}
    _set(monkeypatch, ENCRYPTION_KEY=base64.b64encode(b"short").decode())
    assert config_check.problems() == ["ENCRYPTION_KEY (must be base64 for exactly 32 bytes)"]
    _set(monkeypatch, ENCRYPTION_KEY="not base64 !!")
    assert len(config_check.problems()) == 1
    _set(monkeypatch)
    assert config_check.problems() == []


def test_health_degraded_instead_of_crashing(monkeypatch):
    from main import app
    _set(monkeypatch, ENCRYPTION_KEY="x" * 10)
    with TestClient(app) as client:
        body = client.get("/health").json()
    assert body["status"] == "degraded"
    assert body["missing"] == ["ENCRYPTION_KEY (must be base64 for exactly 32 bytes)"]
    assert not hasattr(app.state, "scout")
