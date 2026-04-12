"""Pydantic models for impact analysis results."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class ImpactResult(BaseModel):
    """Result of analyzing the impact of a schema change.

    Produced by ImpactAnalyzer.analyze() and stored in the impact_analysis
    table in Supabase.
    """

    affected_queries: list[str] = Field(
        default_factory=list,
        description="Query patterns or named queries that may be broken by this change.",
    )
    affected_services: list[str] = Field(
        default_factory=list,
        description="Services, features, or API endpoints likely impacted.",
    )
    affected_indexes: list[str] = Field(
        default_factory=list,
        description="Index names affected by or related to this change.",
    )
    summary: str = Field(
        description="Plain-English explanation of what changed and why it matters.",
    )
    next_action: str = Field(
        description=(
            "What the team should do right now. Uses risk-level framing: "
            "'Safe to deploy.' / 'Review X before deploying.' / "
            "'Do not deploy until...' / 'Stop. Escalate immediately.'"
        ),
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Specific actionable steps the team should take.",
    )

    def to_supabase_payload(self, change_event_id: str) -> dict:
        """Return a dict suitable for inserting into the impact_analysis table."""
        return {
            "change_event_id": change_event_id,
            "affected_queries": self.affected_queries,
            "affected_services": self.affected_services,
            "affected_indexes": self.affected_indexes,
            "summary": self.summary,
            "next_action": self.next_action,
            "recommendations": self.recommendations,
        }
