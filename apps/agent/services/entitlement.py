"""Who gets the product, decided from the `plans` table in the database.

Every plan and its limits live in the `plans` table (supabase/schema.sql). An
org may run only if its plan exists there and it is either on a paid plan or
inside its 14-day trial. Anything we can't prove has no access: an unknown
plan, a missing org, an unreadable trial date. A failed lookup is an error the
caller must handle, never a silent "allow".
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# The plan names the product sells. Startup refuses to run if the database's
# plans table doesn't have every one of them.
REQUIRED_PLANS = ("trial", "solo", "teams", "enterprise")

TRIAL_ENDED_MESSAGE = "Your free trial has ended. Upgrade in Settings to continue."
PLAN_CHECK_FAILED_MESSAGE = "We couldn't check your plan just now. Try again in a minute."
PLANS_MISSING = "plans table missing or incomplete (run supabase/schema.sql or migration 010)"


class EntitlementError(Exception):
    """The plan lookup itself failed (as opposed to the org having no access)."""


def load_plans(supabase) -> dict[str, dict]:
    """The plans table as {name: row}. Raises EntitlementError if it can't be read."""
    try:
        rows = (
            supabase.table("plans")
            .select("name, is_paid, max_databases, max_seats")
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.error("Plans lookup failed: %s", type(exc).__name__)
        raise EntitlementError from exc
    return {r["name"]: r for r in rows}


def plans_problem(supabase) -> str | None:
    """None if every required plan is in the database, else what's wrong."""
    try:
        plans = load_plans(supabase)
    except EntitlementError:
        return PLANS_MISSING
    if not all(name in plans for name in REQUIRED_PLANS):
        return PLANS_MISSING
    return None


def org_has_access(org: dict | None, plans: dict[str, dict], now: datetime | None = None) -> bool:
    """True only if the org's plan is valid and it is paying or provably in its trial."""
    if not org:
        return False
    plan = plans.get(org.get("plan"))
    if plan is None:  # plan not in the plans table: invalid, no access
        return False
    if plan.get("is_paid") or org.get("trial_converted"):
        return True
    ends = org.get("trial_ends_at")
    if not ends:
        return False
    try:
        ends_at = datetime.fromisoformat(str(ends).replace("Z", "+00:00"))
    except ValueError:
        return False
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=timezone.utc)
    return ends_at > (now or datetime.now(timezone.utc))


def _org_rows(supabase, org_ids: list[str]) -> list[dict]:
    try:
        return (
            supabase.table("organizations")
            .select("id, plan, trial_ends_at, trial_converted")
            .in_("id", org_ids)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.error("Org lookup failed: %s", type(exc).__name__)
        raise EntitlementError from exc


def orgs_with_access(supabase, org_ids: set[str]) -> set[str]:
    """Of these org ids, the ones allowed to run. Raises EntitlementError on a failed lookup."""
    if not org_ids:
        return set()
    plans = load_plans(supabase)
    by_id = {r["id"]: r for r in _org_rows(supabase, sorted(org_ids))}
    return {oid for oid in org_ids if org_has_access(by_id.get(oid), plans)}


def require_access(supabase, org_id: str) -> dict:
    """For API routes: the org (with its plan's limits as org["plan_info"]), or
    raise 402 (no access) / 503 (couldn't check)."""
    try:
        plans = load_plans(supabase)
        rows = _org_rows(supabase, [org_id])
    except EntitlementError:
        raise HTTPException(status_code=503, detail=PLAN_CHECK_FAILED_MESSAGE)
    org = rows[0] if rows else None
    if not org_has_access(org, plans):
        raise HTTPException(status_code=402, detail=TRIAL_ENDED_MESSAGE)
    return {**org, "plan_info": plans[org["plan"]]}


def db_limit(org: dict) -> int | None:
    """Database connections this org's plan allows (from the plans table). None = unlimited."""
    return org["plan_info"]["max_databases"]


def db_limit_message(limit: int) -> str:
    return (
        f"Your plan includes {limit} database connections. "
        "Remove one or upgrade your plan to add another."
    )
