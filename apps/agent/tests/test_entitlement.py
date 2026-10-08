"""Plans come from the database; anything unproven has no access."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

import scout.scout_runner as sr
import services.entitlement as ent
from scout.scout_runner import ScoutRunner
from services.entitlement import (
    EntitlementError,
    org_has_access,
    orgs_with_access,
    plans_problem,
    require_access,
)

NOW = datetime(2026, 10, 8, tzinfo=timezone.utc)


def iso(days):
    return (NOW + timedelta(days=days)).isoformat()


def _plan(name, paid, dbs, seats):
    return {"name": name, "is_paid": paid, "max_databases": dbs, "max_seats": seats}


PLAN_ROWS = [_plan("trial", False, 2, 1), _plan("solo", True, 2, 1),
             _plan("teams", True, 10, 10), _plan("enterprise", True, None, None)]
PLANS = {p["name"]: p for p in PLAN_ROWS}


def org(i, plan="trial", days=3, converted=False, ends="default"):
    return {"id": i, "plan": plan, "trial_converted": converted,
            "trial_ends_at": iso(days) if ends == "default" else ends}


def test_trial_access_depends_on_the_date():
    assert org_has_access(org("a", days=3), PLANS, NOW)
    assert not org_has_access(org("a", days=-1), PLANS, NOW)


def test_paid_and_converted_keep_access():
    for plan in ("solo", "teams", "enterprise"):
        assert org_has_access(org("a", plan, days=-30), PLANS, NOW)
    assert org_has_access(org("a", "trial", days=-30, converted=True), PLANS, NOW)


def test_anything_unproven_has_no_access():
    assert not org_has_access(None, PLANS, NOW)
    assert not org_has_access(org("a", "platinum", days=30), PLANS, NOW)  # plan not in the table
    assert not org_has_access(org("a", ends=None), PLANS, NOW)
    assert not org_has_access(org("a", ends="garbage"), PLANS, NOW)
    assert not org_has_access(org("a"), {}, NOW)  # empty plans table: nobody runs


class _Q:
    def __init__(self, fake, table):
        self.fake, self.table, self.rows = fake, table, list(fake.tables.get(table, []))

    def select(self, *a, **k): return self
    def eq(self, c, v): self.rows = [r for r in self.rows if r.get(c) == v]; return self
    def in_(self, c, vals): self.rows = [r for r in self.rows if r.get(c) in vals]; return self

    def execute(self):
        if self.table in self.fake.failing:
            raise RuntimeError("db down")
        return type("R", (), {"data": self.rows})()


class FakeSupabase:
    def __init__(self, tables, failing=()):
        self.tables, self.failing = tables, set(failing)

    def table(self, name): return _Q(self, name)


ORGS = [org("paid", "solo", days=-40), org("trial", days=5), org("expired", days=-2),
        org("weird", "platinum", days=30)]


@pytest.fixture
def frozen(monkeypatch):
    class FrozenDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(ent, "datetime", FrozenDT)


def test_orgs_with_access_uses_the_plans_table(frozen):
    sb = FakeSupabase({"plans": PLAN_ROWS, "organizations": ORGS})
    assert orgs_with_access(sb, {"paid", "trial", "expired", "weird", "ghost"}) == {"paid", "trial"}


@pytest.mark.parametrize("failing", [("plans",), ("organizations",)])
def test_failed_lookup_raises_never_allows(failing):
    sb = FakeSupabase({"plans": PLAN_ROWS, "organizations": ORGS}, failing)
    with pytest.raises(EntitlementError):
        orgs_with_access(sb, {"paid"})


def test_require_access_returns_limits_from_the_table(frozen):
    sb = FakeSupabase({"plans": PLAN_ROWS, "organizations": ORGS})
    got = require_access(sb, "paid")
    assert got["plan_info"]["max_databases"] == 2
    # Change the limit in the table and it changes here, no code change.
    sb.tables["plans"] = [dict(p, max_databases=7) if p["name"] == "solo" else p for p in PLAN_ROWS]
    assert require_access(sb, "paid")["plan_info"]["max_databases"] == 7


def test_require_access_402_and_503(frozen):
    sb = FakeSupabase({"plans": PLAN_ROWS, "organizations": ORGS})
    for oid in ("expired", "weird", "ghost"):
        with pytest.raises(HTTPException) as e:
            require_access(sb, oid)
        assert e.value.status_code == 402
    with pytest.raises(HTTPException) as e:
        require_access(FakeSupabase({"plans": PLAN_ROWS, "organizations": ORGS}, ("plans",)), "paid")
    assert e.value.status_code == 503


def test_plans_problem_catches_missing_or_unreadable_plans():
    assert plans_problem(FakeSupabase({"plans": PLAN_ROWS})) is None
    assert plans_problem(FakeSupabase({"plans": [p for p in PLAN_ROWS if p["name"] != "teams"]}))
    assert plans_problem(FakeSupabase({"plans": []}))
    assert plans_problem(FakeSupabase({"plans": PLAN_ROWS}, ("plans",)))


DBS = [
    {"id": "d-paid", "org_id": "paid", "engine": "postgresql", "is_active": True, "encrypted_connection_string": "x"},
    {"id": "d-exp", "org_id": "expired", "engine": "postgresql", "is_active": True, "encrypted_connection_string": "x"},
    {"id": "d-weird", "org_id": "weird", "engine": "postgresql", "is_active": True, "encrypted_connection_string": "x"},
]


def _runner(monkeypatch, sb):
    monkeypatch.setenv("ENCRYPTION_KEY", "a" * 43 + "=")
    monkeypatch.setattr(sr, "get_supabase", lambda: sb)
    started = []

    async def fake_start(self, db):
        started.append(db["id"])

    monkeypatch.setattr(ScoutRunner, "_start_listener", fake_start)
    return ScoutRunner(), started


@pytest.mark.asyncio
async def test_scout_only_starts_orgs_with_a_valid_active_plan(monkeypatch, frozen):
    runner, started = _runner(monkeypatch, FakeSupabase(
        {"plans": PLAN_ROWS, "organizations": ORGS, "connected_databases": DBS}))
    await runner._reconcile()
    assert started == ["d-paid"]


@pytest.mark.asyncio
async def test_scout_stops_a_listener_when_its_trial_expires(monkeypatch, frozen):
    runner, started = _runner(monkeypatch, FakeSupabase(
        {"plans": PLAN_ROWS, "organizations": ORGS, "connected_databases": DBS[1:2]}))
    running = asyncio.create_task(asyncio.sleep(60))
    runner._listeners["d-exp"] = running
    await runner._reconcile()
    assert "d-exp" not in runner._listeners
    await asyncio.sleep(0)
    assert running.cancelled()


@pytest.mark.asyncio
async def test_scout_leaves_things_alone_when_the_plan_check_fails(monkeypatch, frozen):
    runner, started = _runner(monkeypatch, FakeSupabase(
        {"plans": PLAN_ROWS, "organizations": ORGS, "connected_databases": DBS}, ("plans",)))
    running = asyncio.create_task(asyncio.sleep(60))
    runner._listeners["d-paid"] = running
    await runner._reconcile()
    assert started == [] and runner._listeners == {"d-paid": running}  # nothing new, nothing stopped
    running.cancel()


@pytest.mark.asyncio
async def test_empty_plans_table_means_nothing_runs(monkeypatch, frozen):
    runner, started = _runner(monkeypatch, FakeSupabase(
        {"plans": [], "organizations": ORGS, "connected_databases": DBS}))
    await runner._reconcile()
    assert started == []
