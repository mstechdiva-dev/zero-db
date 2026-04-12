"""Risk scorer for Zero — assigns a risk level to a schema change.

Risk levels (from zero.md):
  LOW      — additive changes: nullable column added, index added, new table created
  MEDIUM   — widening changes: column type widened, index dropped on low-traffic table,
              constraint added to new column
  HIGH     — destructive changes: column dropped, index dropped on critical table,
              NOT NULL added to existing populated column
  CRITICAL — severe structural changes: table dropped, primary key changed/dropped,
              foreign key constraint dropped, column renamed (equivalent to drop+add)
"""

from typing import Literal

RiskLevel = Literal["low", "medium", "high", "critical"]

# change_type values produced by Scout listeners
CRITICAL_CHANGE_TYPES = {
    "table_dropped",
}

HIGH_CHANGE_TYPES = {
    "column_dropped",
    "key_pattern_dropped",
}

MEDIUM_CHANGE_TYPES = {
    "column_modified",
    "index_dropped",
}

LOW_CHANGE_TYPES = {
    "column_added",
    "index_created",
    "table_created",
    "constraint_added",
    "key_pattern_added",
    "ttl_policy_changed",
    "key_type_changed",
}

# Constraint-specific risk rules (applied on top of generic change_type rules)
CRITICAL_CONSTRAINT_TYPES = {"PRIMARY KEY", "FOREIGN KEY"}
HIGH_CONSTRAINT_TYPES = {"UNIQUE", "CHECK"}


def score(
    change_type: str,
    object_type: str,
    before_state: dict | None = None,
    after_state: dict | None = None,
) -> RiskLevel:
    """Return the risk level for a given schema change.

    Parameters
    ----------
    change_type:
        The change_type string stored in the change_events table.
    object_type:
        'table', 'column', 'index', 'constraint', 'collection', 'key_namespace', etc.
    before_state:
        The before snapshot dict — used for constraint-type detection.
    after_state:
        The after snapshot dict — used for constraint-type detection.
    """
    ct = change_type.lower()

    # Handle constraint drops — check what type of constraint was dropped
    if ct == "constraint_dropped":
        constraint_type = _extract_constraint_type(before_state)
        if constraint_type in CRITICAL_CONSTRAINT_TYPES:
            return "critical"
        if constraint_type in HIGH_CONSTRAINT_TYPES:
            return "high"
        return "medium"

    # Handle constraint additions — generally LOW unless it's a PK (rare but possible)
    if ct == "constraint_added":
        constraint_type = _extract_constraint_type(after_state)
        if constraint_type == "PRIMARY KEY":
            return "high"
        return "low"

    # Column modifications need deeper inspection
    if ct == "column_modified":
        return _score_column_modification(before_state, after_state)

    if ct in CRITICAL_CHANGE_TYPES:
        return "critical"

    if ct in HIGH_CHANGE_TYPES:
        return "high"

    if ct in MEDIUM_CHANGE_TYPES:
        return "medium"

    if ct in LOW_CHANGE_TYPES:
        return "low"

    # Default: treat unknown change types as medium to prompt review
    return "medium"


def _extract_constraint_type(state: dict | None) -> str:
    if not state:
        return ""
    return str(state.get("constraint_type", "")).upper()


def _score_column_modification(
    before: dict | None, after: dict | None
) -> RiskLevel:
    """Inspect column modification details to determine risk."""
    if not before or not after:
        return "medium"

    before_nullable = str(before.get("is_nullable", "YES")).upper()
    after_nullable = str(after.get("is_nullable", "YES")).upper()

    # NOT NULL added to an existing column is HIGH — could break existing rows
    if before_nullable == "YES" and after_nullable == "NO":
        return "high"

    # Type changes — try to detect widening vs narrowing
    before_type = str(before.get("data_type", "")).lower()
    after_type = str(after.get("data_type", "")).lower()

    if before_type != after_type:
        if _is_widening(before, after):
            return "medium"
        return "high"

    # Length/precision changes
    before_len = before.get("character_maximum_length")
    after_len = after.get("character_maximum_length")
    if before_len and after_len:
        if int(after_len) > int(before_len):
            return "medium"  # widened
        return "high"  # narrowed

    return "medium"


# Ordered from narrowest to widest — used to detect widening type changes
_TYPE_WIDTH_ORDER = [
    "boolean",
    "smallint",
    "integer",
    "int",
    "bigint",
    "real",
    "double precision",
    "numeric",
    "decimal",
    "char",
    "varchar",
    "character varying",
    "text",
]


def _is_widening(before: dict, after: dict) -> bool:
    """Return True if the type change represents a safe widening."""
    bt = str(before.get("data_type", "")).lower()
    at = str(after.get("data_type", "")).lower()
    try:
        return _TYPE_WIDTH_ORDER.index(at) > _TYPE_WIDTH_ORDER.index(bt)
    except ValueError:
        return False


def label(risk_level: RiskLevel) -> str:
    """Return the display label for a risk level."""
    return risk_level.upper()


def next_action(risk_level: RiskLevel, specific_context: str = "") -> str:
    """Return the plain-English next action for a given risk level."""
    context = f" {specific_context}" if specific_context else ""
    actions = {
        "low": "Safe to deploy. No action required.",
        "medium": f"Review{context} before deploying.",
        "high": f"Do not deploy until this is resolved.{context}",
        "critical": f"Stop. Escalate immediately.{context}",
    }
    return actions.get(risk_level, "Review before deploying.")
