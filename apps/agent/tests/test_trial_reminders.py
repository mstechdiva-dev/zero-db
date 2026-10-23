"""Trial reminders: one email at 3 days left, one at the end, each sent once."""

from datetime import datetime, timedelta, timezone

import pytest

from services.trial_reminders import send_due_reminders

NOW = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)


def iso(days):
    return (NOW + timedelta(days=days)).isoformat()


class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.upd = db, table, [], None

    def select(self, *a, **k): return self
    def eq(self, c, v): self.filters.append(("eq", c, v)); return self
    def lt(self, c, v): self.filters.append(("lt", c, v)); return self
    def update(self, vals): self.upd = vals; return self

    def execute(self):
        rows = self.db[self.table]
        def ok(r):
            for op, c, v in self.filters:
                if op == "eq" and r.get(c) != v: return False
                if op == "lt" and not r.get(c) < v: return False
            return True
        hit = [r for r in rows if ok(r)]
        if self.upd is not None:
            for r in hit: r.update(self.upd)
        return type("R", (), {"data": hit})()


class FakeSupabase:
    def __init__(self, orgs, users):
        self.db = {"organizations": orgs, "users": users}

    def table(self, name): return _Q(self.db, name)


class FakeEmail:
    def __init__(self, smtp_host="smtp.example.com", ok=True):
        self.smtp_host, self.ok, self.sent = smtp_host, ok, []

    async def send_alert(self, recipients, subject, html):
        self.sent.append((list(recipients), subject, html))
        return self.ok


def org(i, days, stage=0, plan="trial", converted=False):
    return {"id": i, "plan": plan, "trial_converted": converted,
            "trial_ends_at": iso(days), "trial_reminder_stage": stage}


USERS = [{"org_id": "a", "email": "a@x.com"}, {"org_id": "b", "email": "b@x.com"},
         {"org_id": "c", "email": "c@x.com"}, {"org_id": "d", "email": "d@x.com"}]


@pytest.mark.asyncio
async def test_three_day_and_ended_emails_go_to_the_right_orgs():
    sb = FakeSupabase([org("a", 2.5), org("b", -1), org("c", 10), org("d", 1, plan="solo")], USERS)
    mail = FakeEmail()
    assert await send_due_reminders(sb, mail, NOW) == 2
    by_to = {m[0][0]: m for m in mail.sent}
    assert "ends in 2 days" in by_to["a@x.com"][1]
    assert "has ended" in by_to["b@x.com"][1]
    assert "c@x.com" not in by_to and "d@x.com" not in by_to  # far off / paying
    stages = {o["id"]: o["trial_reminder_stage"] for o in sb.db["organizations"]}
    assert stages == {"a": 1, "b": 2, "c": 0, "d": 0}


@pytest.mark.asyncio
async def test_each_email_is_sent_once():
    sb = FakeSupabase([org("a", 2)], USERS)
    mail = FakeEmail()
    await send_due_reminders(sb, mail, NOW)
    await send_due_reminders(sb, mail, NOW)
    assert len(mail.sent) == 1
    later = NOW + timedelta(days=3)  # trial now over: the "ended" email follows
    await send_due_reminders(sb, mail, later)
    await send_due_reminders(sb, mail, later)
    assert [m[1] for m in mail.sent][1] == "Your SchemaZero trial has ended"
    assert len(mail.sent) == 2


@pytest.mark.asyncio
async def test_failed_send_is_retried_not_marked():
    sb = FakeSupabase([org("a", 2)], USERS)
    assert await send_due_reminders(sb, FakeEmail(ok=False), NOW) == 0
    assert sb.db["organizations"][0]["trial_reminder_stage"] == 0
    assert await send_due_reminders(sb, FakeEmail(ok=True), NOW) == 1


@pytest.mark.asyncio
async def test_no_smtp_means_nothing_sent_or_marked():
    sb = FakeSupabase([org("a", -1)], USERS)
    assert await send_due_reminders(sb, FakeEmail(smtp_host=""), NOW) == 0
    assert sb.db["organizations"][0]["trial_reminder_stage"] == 0


@pytest.mark.asyncio
async def test_lookup_error_is_swallowed():
    class Broken:
        def table(self, name): raise RuntimeError("no such column trial_reminder_stage")
    assert await send_due_reminders(Broken(), FakeEmail(), NOW) == 0
