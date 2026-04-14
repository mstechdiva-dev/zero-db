"""Unit tests for apps/agent/zero/risk_scorer.py

Covers every risk level and all special-case branches:
- Simple change_type dispatch (LOW / MEDIUM / HIGH / CRITICAL)
- constraint_dropped with different constraint types
- constraint_added with PK vs other types
- column_modified: NOT NULL added, type widening, type narrowing, length changes
- Unknown change_type defaults to MEDIUM
- label() and next_action() helpers
"""

import sys
import os

# Make the agent package importable without a full install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from zero.risk_scorer import score, label, next_action


# ---------------------------------------------------------------------------
# LOW risk — additive changes
# ---------------------------------------------------------------------------

class TestLowRisk:
    def test_column_added(self):
        assert score("column_added", "column") == "low"

    def test_index_created(self):
        assert score("index_created", "index") == "low"

    def test_table_created(self):
        assert score("table_created", "table") == "low"

    def test_key_pattern_added(self):
        assert score("key_pattern_added", "key_namespace") == "low"

    def test_ttl_policy_changed(self):
        assert score("ttl_policy_changed", "key_namespace") == "low"

    def test_key_type_changed(self):
        assert score("key_type_changed", "key_namespace") == "low"

    def test_constraint_added_check(self):
        after = {"constraint_type": "CHECK"}
        assert score("constraint_added", "constraint", after_state=after) == "low"

    def test_constraint_added_unique(self):
        after = {"constraint_type": "UNIQUE"}
        assert score("constraint_added", "constraint", after_state=after) == "low"

    def test_constraint_added_fk(self):
        after = {"constraint_type": "FOREIGN KEY"}
        assert score("constraint_added", "constraint", after_state=after) == "low"

    def test_constraint_added_no_state(self):
        # Default when no after_state provided — non-PK additive
        assert score("constraint_added", "constraint") == "low"

    def test_column_modified_nullable_both_yes(self):
        before = {"is_nullable": "YES", "data_type": "text"}
        after = {"is_nullable": "YES", "data_type": "text"}
        # No meaningful change → medium (no specific low path)
        result = score("column_modified", "column", before_state=before, after_state=after)
        assert result in ("low", "medium")


# ---------------------------------------------------------------------------
# MEDIUM risk — widening or index drops
# ---------------------------------------------------------------------------

class TestMediumRisk:
    def test_index_dropped(self):
        assert score("index_dropped", "index") == "medium"

    def test_column_modified_type_widening(self):
        before = {"is_nullable": "YES", "data_type": "integer"}
        after = {"is_nullable": "YES", "data_type": "bigint"}
        assert score("column_modified", "column", before_state=before, after_state=after) == "medium"

    def test_column_modified_varchar_widened(self):
        before = {"is_nullable": "YES", "data_type": "character varying", "character_maximum_length": 50}
        after = {"is_nullable": "YES", "data_type": "character varying", "character_maximum_length": 255}
        assert score("column_modified", "column", before_state=before, after_state=after) == "medium"

    def test_column_modified_no_state_defaults_medium(self):
        assert score("column_modified", "column") == "medium"

    def test_column_modified_smallint_to_integer(self):
        before = {"is_nullable": "YES", "data_type": "smallint"}
        after = {"is_nullable": "YES", "data_type": "integer"}
        assert score("column_modified", "column", before_state=before, after_state=after) == "medium"

    def test_constraint_dropped_no_type_defaults_medium(self):
        before = {"constraint_type": ""}
        assert score("constraint_dropped", "constraint", before_state=before) == "medium"

    def test_constraint_dropped_unknown_type_defaults_medium(self):
        before = {"constraint_type": "EXCLUSION"}
        assert score("constraint_dropped", "constraint", before_state=before) == "medium"


# ---------------------------------------------------------------------------
# HIGH risk — destructive column / index / constraint changes
# ---------------------------------------------------------------------------

class TestHighRisk:
    def test_column_dropped(self):
        assert score("column_dropped", "column") == "high"

    def test_key_pattern_dropped(self):
        assert score("key_pattern_dropped", "key_namespace") == "high"

    def test_column_modified_not_null_added(self):
        before = {"is_nullable": "YES", "data_type": "text"}
        after = {"is_nullable": "NO", "data_type": "text"}
        assert score("column_modified", "column", before_state=before, after_state=after) == "high"

    def test_column_modified_type_narrowing(self):
        before = {"is_nullable": "YES", "data_type": "bigint"}
        after = {"is_nullable": "YES", "data_type": "smallint"}
        assert score("column_modified", "column", before_state=before, after_state=after) == "high"

    def test_column_modified_varchar_narrowed(self):
        before = {"is_nullable": "YES", "data_type": "character varying", "character_maximum_length": 255}
        after = {"is_nullable": "YES", "data_type": "character varying", "character_maximum_length": 50}
        assert score("column_modified", "column", before_state=before, after_state=after) == "high"

    def test_constraint_dropped_unique(self):
        before = {"constraint_type": "UNIQUE"}
        assert score("constraint_dropped", "constraint", before_state=before) == "high"

    def test_constraint_dropped_check(self):
        before = {"constraint_type": "CHECK"}
        assert score("constraint_dropped", "constraint", before_state=before) == "high"

    def test_constraint_added_primary_key(self):
        after = {"constraint_type": "PRIMARY KEY"}
        assert score("constraint_added", "constraint", after_state=after) == "high"


# ---------------------------------------------------------------------------
# CRITICAL risk — table drops and structural changes
# ---------------------------------------------------------------------------

class TestCriticalRisk:
    def test_table_dropped(self):
        assert score("table_dropped", "table") == "critical"

    def test_constraint_dropped_primary_key(self):
        before = {"constraint_type": "PRIMARY KEY"}
        assert score("constraint_dropped", "constraint", before_state=before) == "critical"

    def test_constraint_dropped_foreign_key(self):
        before = {"constraint_type": "FOREIGN KEY"}
        assert score("constraint_dropped", "constraint", before_state=before) == "critical"

    def test_constraint_dropped_primary_key_lowercase(self):
        # constraint_type may come back in varying cases from DB drivers
        before = {"constraint_type": "primary key"}
        assert score("constraint_dropped", "constraint", before_state=before) == "critical"


# ---------------------------------------------------------------------------
# Unknown change_type fallback
# ---------------------------------------------------------------------------

class TestUnknownChangeType:
    def test_unknown_defaults_to_medium(self):
        assert score("some_new_change_type", "object") == "medium"

    def test_empty_string_defaults_to_medium(self):
        assert score("", "object") == "medium"


# ---------------------------------------------------------------------------
# label() helper
# ---------------------------------------------------------------------------

class TestLabel:
    @pytest.mark.parametrize("level,expected", [
        ("low", "LOW"),
        ("medium", "MEDIUM"),
        ("high", "HIGH"),
        ("critical", "CRITICAL"),
    ])
    def test_label_uppercase(self, level, expected):
        assert label(level) == expected


# ---------------------------------------------------------------------------
# next_action() helper
# ---------------------------------------------------------------------------

class TestNextAction:
    def test_low_safe_to_deploy(self):
        result = next_action("low")
        assert "Safe to deploy" in result
        assert "No action required" in result

    def test_medium_review(self):
        result = next_action("medium")
        assert "Review" in result or "review" in result

    def test_high_do_not_deploy(self):
        result = next_action("high")
        assert "Do not deploy" in result or "do not deploy" in result

    def test_critical_escalate(self):
        result = next_action("critical")
        assert "Escalate" in result or "escalate" in result

    def test_medium_with_context(self):
        result = next_action("medium", specific_context="users table")
        assert "users table" in result

    def test_unknown_level_returns_string(self):
        result = next_action("unknown_level")
        assert isinstance(result, str)
        assert len(result) > 0
