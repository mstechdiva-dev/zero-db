"""Zero Runner — main orchestrator for impact analysis and alert dispatch.

Triggered by Scout via POST /internal/analyze when a new change_event is
written to Supabase. Zero reads the event, scores risk, runs impact analysis
using the Claude API, writes results to impact_analysis, updates the risk_level
on the change event, and fires alerts.
"""

import logging

from services.supabase_service import get_supabase
from zero.risk_scorer import score as score_risk, next_action
from zero.impact_analyzer import ImpactAnalyzer
from zero.alert_dispatcher import AlertDispatcher

logger = logging.getLogger(__name__)


class ZeroRunner:
    def __init__(self, agent_prompts: dict[str, str]):
        self._agent_prompts = agent_prompts

    async def analyze(self, change_event_id: str) -> dict:
        """Run the full Zero pipeline for a given change event ID.

        1. Fetch the change event from Supabase
        2. Score risk level
        3. Run impact analysis via Claude API
        4. Write impact_analysis record to Supabase
        5. Update risk_level on the change_event
        6. Dispatch alerts
        """
        supabase = get_supabase()

        # 1. Fetch change event
        result = (
            supabase.table("change_events")
            .select("*")
            .eq("id", change_event_id)
            .single()
            .execute()
        )
        if not result.data:
            logger.error("Change event not found: %s", change_event_id)
            return {"error": "change_event not found"}

        change_event = result.data
        org_id = change_event["org_id"]

        # 2. Score risk
        risk_level = score_risk(
            change_type=change_event.get("change_type", ""),
            object_type=change_event.get("object_type", ""),
            before_state=change_event.get("before_state"),
            after_state=change_event.get("after_state"),
        )

        # 3. Run impact analysis
        analyzer = ImpactAnalyzer(agent_prompts=self._agent_prompts)
        impact = await analyzer.analyze(
            change_event=change_event,
            risk_level=risk_level,
        )

        # Always enforce risk-level framing — don't trust the AI to match exactly
        impact["next_action"] = next_action(risk_level)

        # 4. Write impact_analysis record
        impact_record = {
            "change_event_id": change_event_id,
            "affected_queries": impact.get("affected_queries", []),
            "affected_services": impact.get("affected_services", []),
            "affected_indexes": impact.get("affected_indexes", []),
            "summary": impact.get("summary", ""),
            "next_action": impact.get("next_action", ""),
            "recommendations": impact.get("recommendations", []),
        }
        try:
            supabase.table("impact_analysis").insert(impact_record).execute()
        except Exception as exc:
            logger.error("Failed to write impact_analysis for event %s: %s", change_event_id, exc)

        # 5. Update risk_level on change_event
        try:
            supabase.table("change_events").update({"risk_level": risk_level}).eq(
                "id", change_event_id
            ).execute()
        except Exception as exc:
            logger.error("Failed to update risk_level for event %s: %s", change_event_id, exc)

        # 6. Dispatch alerts
        dispatcher = AlertDispatcher(supabase_client=supabase)
        try:
            await dispatcher.dispatch(
                org_id=org_id,
                change_event={**change_event, "id": change_event_id},
                impact=impact,
                risk_level=risk_level,
            )
        except Exception as exc:
            logger.error("Alert dispatch failed for event %s: %s", change_event_id, exc)

        logger.info(
            "Zero analysis complete: event=%s risk=%s", change_event_id, risk_level
        )
        return {
            "change_event_id": change_event_id,
            "risk_level": risk_level,
            "summary": impact.get("summary", ""),
            "next_action": impact.get("next_action", ""),
        }
