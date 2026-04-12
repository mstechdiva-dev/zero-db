"""Impact Analyzer — main entry point for the impact package.

Accepts a change description dict (compatible with DiffResult fields) and
returns an ImpactResult by combining heuristic tracing (QueryTracer,
IndexTracer) with optional Claude API analysis via the Zero agent prompt.
"""

import json
import logging
import os
import sys
from typing import Optional

_pkg_root = os.path.abspath(os.path.dirname(__file__))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from models import ImpactResult  # noqa: E402
from query_tracer import QueryTracer  # noqa: E402
from index_tracer import IndexTracer  # noqa: E402

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """Analyze the impact of a schema change.

    Uses heuristic tracers for quick local analysis and optionally enriches
    the result using the Claude API (Zero agent) when an anthropic_service
    is provided.

    Parameters
    ----------
    anthropic_service:
        Optional AnthropicService instance pre-loaded with the zero.md
        system prompt. When provided, AI analysis enriches the result.
        When None, only heuristic analysis is returned.
    """

    def __init__(self, anthropic_service=None):
        self._anthropic = anthropic_service
        self._query_tracer = QueryTracer()
        self._index_tracer = IndexTracer()

    def analyze_sync(self, change: dict, risk_level: str = "medium") -> ImpactResult:
        """Run heuristic-only analysis (no Claude API call). Synchronous.

        Parameters
        ----------
        change:
            Dict with keys: change_type, object_type, object_name,
            schema_name (optional), before_state (optional), after_state (optional),
            human_readable_summary (optional).
        risk_level:
            Scored risk level: 'low', 'medium', 'high', or 'critical'.
        """
        change_type = change.get("change_type", "schema_change")
        object_type = change.get("object_type", "object")
        object_name = change.get("object_name", "unknown")
        schema_name = change.get("schema_name")
        before_state = change.get("before_state")
        after_state = change.get("after_state")

        affected_queries = self._query_tracer.trace(
            change_type=change_type,
            object_type=object_type,
            object_name=object_name,
            schema_name=schema_name,
            before_state=before_state,
            after_state=after_state,
        )
        affected_indexes = self._index_tracer.trace(
            change_type=change_type,
            object_type=object_type,
            object_name=object_name,
            before_state=before_state,
            after_state=after_state,
        )

        summary = change.get("human_readable_summary") or (
            f"{change_type.replace('_', ' ').title()} on "
            f"{object_type} '{object_name}'."
        )

        return ImpactResult(
            affected_queries=affected_queries,
            affected_services=[],
            affected_indexes=affected_indexes,
            summary=summary,
            next_action=_default_next_action(risk_level),
            recommendations=_default_recommendations(change_type),
        )

    async def analyze(self, change: dict, risk_level: str = "medium") -> ImpactResult:
        """Run full analysis — heuristics + optional Claude API enrichment."""
        base = self.analyze_sync(change, risk_level)

        if not self._anthropic:
            return base

        try:
            return await self._enrich_with_ai(change, base, risk_level)
        except Exception as exc:
            logger.warning("AI enrichment failed, using heuristic result: %s", exc)
            return base

    async def _enrich_with_ai(
        self, change: dict, base: ImpactResult, risk_level: str
    ) -> ImpactResult:
        prompt = f"""A schema change was detected. Enrich the impact analysis.

CHANGE:
- type: {change.get('change_type')}
- object: {change.get('object_type')} '{change.get('object_name')}'
- schema: {change.get('schema_name', 'public')}
- risk: {risk_level.upper()}
- summary: {base.summary}

Already identified:
- affected_queries: {json.dumps(base.affected_queries)}
- affected_indexes: {json.dumps(base.affected_indexes)}

Respond in JSON (no markdown, no code blocks):
{{
  "affected_services": ["<service or API route likely impacted>"],
  "additional_recommendations": ["<specific actionable recommendation>"]
}}"""

        raw = await self._anthropic.chat(message=prompt, history=[])
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(cleaned)
            return ImpactResult(
                affected_queries=base.affected_queries,
                affected_services=data.get("affected_services", []),
                affected_indexes=base.affected_indexes,
                summary=base.summary,
                next_action=base.next_action,
                recommendations=base.recommendations + data.get("additional_recommendations", []),
            )
        except (json.JSONDecodeError, ValueError):
            return base


def _default_next_action(risk_level: str) -> str:
    actions = {
        "low": "Safe to deploy. No action required.",
        "medium": "Review the change before deploying.",
        "high": "Do not deploy until this change has been reviewed and verified safe.",
        "critical": "Stop. Escalate immediately. Do not deploy.",
    }
    return actions.get(risk_level.lower(), "Review before deploying.")


def _default_recommendations(change_type: str) -> list[str]:
    recs: dict[str, list[str]] = {
        "table_dropped": [
            "Verify no application code references this table.",
            "Check for foreign key references to this table in other tables.",
            "Ensure a backup exists before confirming the drop.",
        ],
        "column_dropped": [
            "Search the codebase for any SELECT, INSERT, or UPDATE referencing this column.",
            "Update ORM models to remove the dropped column.",
            "Verify no API responses include this column field.",
        ],
        "column_modified": [
            "Review queries that read from or write to this column for type compatibility.",
            "Test with existing data under the new column definition.",
        ],
        "index_dropped": [
            "Profile queries on this table to check for performance regressions.",
            "Re-add the index if query performance degrades.",
        ],
        "constraint_dropped": [
            "Review application-level validation to maintain data integrity.",
            "Check that removing this constraint does not allow invalid data.",
        ],
    }
    return recs.get(
        change_type,
        ["Review the change and verify it does not break existing functionality."],
    )
