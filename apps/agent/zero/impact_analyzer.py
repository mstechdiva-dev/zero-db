"""Impact Analyzer — uses Claude API (via Zero's system prompt) to analyze
a schema change event and produce a structured ImpactResult.
"""

import json
import logging
import os
from typing import Optional

from services.anthropic_service import AnthropicService

logger = logging.getLogger(__name__)

ZERO_AGENT_NAME = "zero"


class ImpactAnalyzer:
    """Analyzes a schema change event using the Zero agent system prompt.

    Loads zero.md at instantiation so the agent behavior can be updated
    without touching Python code.
    """

    def __init__(self, agent_prompts: dict[str, str]):
        zero_prompt = agent_prompts.get(ZERO_AGENT_NAME)
        if not zero_prompt:
            raise RuntimeError("Zero agent prompt not loaded — check agents/zero.md")
        self._service = AnthropicService(
            system_prompt=zero_prompt,
            agent_name=ZERO_AGENT_NAME,
        )

    async def analyze(
        self,
        change_event: dict,
        risk_level: str,
    ) -> dict:
        """Call Zero via Claude API and return a structured impact result.

        Returns a dict matching the impact_analysis table schema:
          - affected_queries: list of query patterns that could break
          - affected_services: list of services likely impacted
          - affected_indexes: list of indexes affected
          - summary: plain-English explanation of what changed
          - next_action: what the team should do right now
          - recommendations: list of recommended actions
        """
        prompt = self._build_prompt(change_event, risk_level)

        try:
            raw = await self._service.chat(message=prompt, history=[])
            return self._parse_response(raw, risk_level, change_event)
        except Exception as exc:
            logger.error("Impact analysis failed for event %s: %s", change_event.get("id"), exc)
            return self._fallback_result(risk_level, change_event)

    def _build_prompt(self, change_event: dict, risk_level: str) -> str:
        change_type = change_event.get("change_type", "unknown")
        object_type = change_event.get("object_type", "unknown")
        object_name = change_event.get("object_name", "unknown")
        schema_name = change_event.get("schema_name", "public")
        before_state = json.dumps(change_event.get("before_state"), indent=2)
        after_state = json.dumps(change_event.get("after_state"), indent=2)

        return f"""A schema change has been detected. Analyze the impact and respond in the JSON format below.

SCHEMA CHANGE DETAILS:
- Change type: {change_type}
- Object type: {object_type}
- Object name: {object_name}
- Schema: {schema_name}
- Risk level: {risk_level.upper()}
- Before state: {before_state}
- After state: {after_state}

Respond with a JSON object (no markdown, no code blocks, raw JSON only):
{{
  "affected_queries": ["<query pattern or description>"],
  "affected_services": ["<service or feature likely impacted>"],
  "affected_indexes": ["<index name if relevant>"],
  "summary": "<plain English explanation of what changed and why it matters>",
  "next_action": "<exactly what the team should do right now — use the risk level framing>",
  "recommendations": ["<specific actionable recommendation>"]
}}"""

    def _parse_response(self, raw: str, risk_level: str, change_event: dict) -> dict:
        """Parse the JSON response from Zero. Falls back gracefully."""
        # Strip any accidental markdown fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            result = json.loads(cleaned)
            # Ensure all required keys are present
            result.setdefault("affected_queries", [])
            result.setdefault("affected_services", [])
            result.setdefault("affected_indexes", [])
            result.setdefault("summary", f"{change_event.get('change_type')} detected on {change_event.get('object_name')}")
            result.setdefault("next_action", self._default_next_action(risk_level))
            result.setdefault("recommendations", [])
            return result
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to parse Zero response as JSON: %s", exc)
            return self._fallback_result(risk_level, change_event, raw_summary=raw)

    def _fallback_result(
        self, risk_level: str, change_event: dict, raw_summary: Optional[str] = None
    ) -> dict:
        return {
            "affected_queries": [],
            "affected_services": [],
            "affected_indexes": [],
            "summary": raw_summary or (
                f"{change_event.get('change_type', 'Schema change')} detected on "
                f"{change_event.get('object_name', 'unknown object')}."
            ),
            "next_action": self._default_next_action(risk_level),
            "recommendations": ["Review the change manually and verify no breaking changes were introduced."],
        }

    @staticmethod
    def _default_next_action(risk_level: str) -> str:
        actions = {
            "low": "Safe to deploy. No action required.",
            "medium": "Review the change before deploying.",
            "high": "Do not deploy until this change has been reviewed and verified safe.",
            "critical": "Stop. Escalate immediately. Do not deploy.",
        }
        return actions.get(risk_level.lower(), "Review before deploying.")
