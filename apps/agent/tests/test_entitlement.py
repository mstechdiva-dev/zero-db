"""Expired, unpaid trials are switched off; paying and in-trial orgs stay on."""

from datetime import datetime, timedelta, timezone

import pytest

from scout.scout_runner import ScoutRunner
from services.entitlement import org_has_access, orgs_with_access

NOW = datetime(2026, 10, 8, tzinfo=timezone.utc)


def iso(days):
    return (NOW + timedelta(days=days)).isoformat()


def test_in_trial_has_access():
    assert org_has_access({"plan": "trial", "trial_ends_at": iso(3), "trial_converted": False}, NOW)


def test_expired_trial_loses_access():
    assert not org_has_access({"plan": "trial", "trial_ends_at": iso(-1), "trial_converted": False}, NOW)


def test_paid_plan_keeps_access_even_after_trial_date():
    for plan in ("solo", "teams", "enterprise"):
        assert org_has_access({"plan": plan, "trial_ends_at": iso(-30), "trial_converted": False}, NOW)
    assert org_has_access({"plan": "trial", "trial_ends_at": iso(-30), "trial_converted": True}, NOW)


def test_missing_or_unreadable_data_fails_open():
    assert org_has_access(None, NOW)
    assert org_has_access({"plan": "trial", "trial_ends_at": None, "trial_converted": False}, NOW)
    assert org_has_access({"plan": "trial", "trial_ends_at": "garbage", "trial_converted": False}, NOW)


class _Query:
    def __init__(self, rows, fail=False):
        self.rows, self.fail = rows, fail

    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def in_(self, col, vals):
        self.rows = [r for r in self.rows if r.get(col) in vals]
        return self

    def execute(self):
        if self.fail:
            raise RuntimeError("db down")
        return type("R", (), {"data": self.rows})()


class _Supabase:
    def __init__(self, orgs, dbs, fail_orgs=False):
        self.orgs, self.dbs, self.fail_orgs = orgs, dbs, fail_orgs

    def table(self, name):
        if name == "organizations":
            return _Query(list(self.orgs), self.fail_orgs)
        return _Query(list(self.dbs))


ORGS = [
    {"id": "paid", "plan": "solo", "trial_ends_at": iso(-40), "trial_converted": True},
    {"id": "trial", "plan": "trial", "trial_ends_at": iso(5), "trial_converted": False},
    {"id": "expired", "plan": "trial", "trial_ends_at": iso(-2), "trial_converted": False},
]


def test_orgs_with_access_filters_expired_only(monkeypatch):
    import services.entitlement as ent

    class FrozenDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(ent, "datetime", FrozenDT)
    got = orgs_with_access(_Supabase(ORGS, []), {"paid", "trial", "expired"})
    assert got == {"paid", "trial"}


def test_trial_lookup_failure_leaves_everyone_on():
    got = orgs_with_access(_Supabase(ORGS, [], fail_orgs=True), {"paid", "expired"})
    assert got == {"paid", "expired"}


@pytest.mark.asyncio
async def test_scout_stops_expired_and_starts_paying(monkeypatch):
    import scout.scout_runner as sr
    import services.entitlement as ent

    class FrozenDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(ent, "datetime", FrozenDT)
    monkeypatch.setenv("ENCRYPTION_KEY", "a" * 43 + "=")
    dbs = [
        {"id": "d-paid", "org_id": "paid", "engine": "postgresql", "encrypted_connection_string": "x"},
        {"id": "d-exp", "org_id": "expired", "engine": "postgresql", "encrypted_connection_string": "x"},
    ]
    monkeypatch.setattr(sr, "get_supabase", lambda: _Supabase(ORGS, dbs))
    started = []

    async def fake_start(self, db):
        started.append(db["id"])

    monkeypatch.setattr(ScoutRunner, "_start_listener", fake_start)
    runner = ScoutRunner()
    await runner._reconcile()
    assert started == ["d-paid"]


@pytest.mark.asyncio
async def test_scout_stops_a_listener_when_its_trial_expires(monkeypatch):
    import asyncio
    import scout.scout_runner as sr
    import services.entitlement as ent

    class FrozenDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(ent, "datetime", FrozenDT)
    monkeypatch.setenv("ENCRYPTION_KEY", "a" * 43 + "=")
    dbs = [{"id": "d-exp", "org_id": "expired", "engine": "postgresql", "encrypted_connection_string": "x"}]
    monkeypatch.setattr(sr, "get_supabase", lambda: _Supabase(ORGS, dbs))
    runner = ScoutRunner()
    running = asyncio.create_task(asyncio.sleep(60))
    runner._listeners["d-exp"] = running
    await runner._reconcile()
    assert "d-exp" not in runner._listeners
    assert running.cancelled() or running.done()
