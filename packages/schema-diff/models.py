"""Pydantic models for schema diff results.

All diff engines return a DiffResult that can be serialised to JSON and
stored in the Supabase change_events table.
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

ChangeType = Literal[
    "column_added",
    "column_dropped",
    "column_modified",
    "table_created",
    "table_dropped",
    "index_created",
    "index_dropped",
    "constraint_added",
    "constraint_dropped",
    "collection_created",
    "collection_dropped",
    "key_pattern_added",
    "key_pattern_dropped",
    "key_type_changed",
    "ttl_policy_changed",
    "schema_change",
]


class DiffResult(BaseModel):
    """Standardised result of comparing two schema snapshots.

    Matches the change_events table schema in Supabase.
    """

    change_type: ChangeType
    object_type: str
    object_name: str
    schema_name: Optional[str] = None
    before_state: Optional[Any] = None
    after_state: Optional[Any] = None
    human_readable_summary: str = ""

    def to_change_event_payload(
        self,
        org_id: str,
        database_id: str,
    ) -> dict:
        """Return a dict suitable for inserting into change_events."""
        return {
            "org_id": org_id,
            "database_id": database_id,
            "change_type": self.change_type,
            "object_type": self.object_type,
            "object_name": self.object_name,
            "schema_name": self.schema_name,
            "before_state": self.before_state,
            "after_state": self.after_state,
        }
