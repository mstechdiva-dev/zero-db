"""Trial reminder emails: one at 3 days left, one when the trial ends.

Runs from the Scout loop. Each org gets each email once (trial_reminder_stage),
and only if SMTP is set up. Everything here fails soft: a problem sending a
reminder must never stop Scout from watching databases.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

SOON = timedelta(days=3)


def _dashboard_url() -> str:
    return os.environ.get("DASHBOARD_URL", "https://schemazero.com").rstrip("/")


def _email(stage: int, days_left: int) -> tuple[str, str]:
    link = f"{_dashboard_url()}/dashboard/settings"
    if stage == 2:
        return (
            "Your SchemaZero trial has ended",
            f"<p>Your 14-day SchemaZero trial has ended, so we've stopped watching your "
            f"databases and sending alerts.</p>"
            f"<p><a href=\"{link}\">Upgrade to Solo ($19/month)</a> and watching starts again "
            f"within a minute.</p>",
        )
    days = "less than a day" if days_left < 1 else f"{days_left} day{'s' if days_left != 1 else ''}"
    return (
        f"Your SchemaZero trial ends in {days}",
        f"<p>Your free SchemaZero trial ends in {days}. After that we stop watching your "
        f"databases and sending alerts.</p>"
        f"<p><a href=\"{link}\">Upgrade to Solo ($19/month)</a> to keep it running.</p>",
    )


async def send_due_reminders(supabase, email_service, now: datetime | None = None) -> int:
    """Send any reminders that are due. Returns how many emails went out."""
    if not getattr(email_service, "smtp_host", ""):
        return 0  # no SMTP set up: nothing to send, nothing to mark
    now = now or datetime.now(timezone.utc)
    sent = 0
    try:
        orgs = (
            supabase.table("organizations")
            .select("id, trial_ends_at, trial_reminder_stage")
            .eq("plan", "trial")
            .eq("trial_converted", False)
            .lt("trial_reminder_stage", 2)
            .execute()
            .data
            or []
        )
    except Exception as exc:  # also covers a database that predates migration 009
        logger.warning("Trial reminder lookup failed: %s", type(exc).__name__)
        return 0

    for org in orgs:
        try:
            ends = datetime.fromisoformat(str(org["trial_ends_at"]).replace("Z", "+00:00"))
            if ends.tzinfo is None:
                ends = ends.replace(tzinfo=timezone.utc)
            stage = int(org.get("trial_reminder_stage") or 0)
            if ends <= now:
                target = 2
            elif ends - now <= SOON:
                target = 1
            else:
                continue
            if stage >= target:
                continue

            users = (
                supabase.table("users").select("email").eq("org_id", org["id"]).execute().data or []
            )
            recipients = [u["email"] for u in users if u.get("email")]
            if not recipients:
                continue
            days_left = max(0, (ends - now).days)
            subject, html = _email(target, days_left)
            if await email_service.send_alert(recipients, subject, html):
                supabase.table("organizations").update({"trial_reminder_stage": target}).eq(
                    "id", org["id"]
                ).execute()
                sent += 1
        except Exception as exc:
            logger.warning("Trial reminder failed for one org: %s", type(exc).__name__)
    return sent
