"""Who still gets the product: paying orgs and orgs inside their 14-day trial.

Mirrors the website's check (dashboard layout) so the backend stops watching
and alerting for expired trials too, not just the dashboard pages.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

PAID_PLANS = {"solo", "teams", "enterprise"}
TRIAL_ENDED_MESSAGE = "Your free trial has ended. Upgrade in Settings to continue."


def org_has_access(org: dict | None, now: datetime | None = None) -> bool:
    """True if the org is paying or its trial has not ended.

    An org we can't find, or a trial end we can't read, fails open: a data
    problem should not switch a customer off.
    """
    if not org:
        return True
    if org.get("plan") in PAID_PLANS or org.get("trial_converted"):
        return True
    ends = org.get("trial_ends_at")
    if not ends:
        return True
    try:
        ends_at = datetime.fromisoformat(str(ends).replace("Z", "+00:00"))
    except ValueError:
        return True
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=timezone.utc)
    return ends_at > (now or datetime.now(timezone.utc))


def orgs_with_access(supabase, org_ids: set[str]) -> set[str]:
    """Of these org ids, the ones that still have access (one query)."""
    if not org_ids:
        return set()
    try:
        rows = (
            supabase.table("organizations")
            .select("id, plan, trial_ends_at, trial_converted")
            .in_("id", sorted(org_ids))
            .execute()
            .data
            or []
        )
    except Exception as exc:  # fail open
        logger.error("Trial check failed, leaving all orgs on: %s", type(exc).__name__)
        return set(org_ids)
    by_id = {r["id"]: r for r in rows}
    return {oid for oid in org_ids if org_has_access(by_id.get(oid))}
