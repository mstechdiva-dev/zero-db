"""Unit tests for packages/schema-diff/engines/postgres_diff.py

Tests all detected change types:
- Columns: added, dropped, modified (type, nullable, default, length)
- Tables: created, dropped (derived from column presence)
- Indexes: created, dropped
- Constraints: added, dropped

All tests run without any database connection — purely in-memory dicts.
"""

import sys
import os

# Make packages/schema-diff importable
_schema_diff_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages", "schema-diff")
)
sys.path.insert(0, _schema_diff_root)

import pytest
from engines.postgres_diff import PostgresDiff
from models import DiffResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def differ():
    return PostgresDiff()


def _base_snapshot():
    """A minimal but complete snapshot with one table and one index."""
    return {
        "columns": [
            {
                "table_schema": "public",
                "table_name": "users",
                "column_name": "id",
                "data_type": "integer",
                "is_nullable": "NO",
                "column_default": None,
                "character_maximum_length": None,
                "numeric_precision": 32,
            },
            {
                "table_schema": "public",
                "table_name": "users",
                "column_name": "email",
                "data_type": "character varying",
                "is_nullable": "YES",
                "column_default": None,
                "character_maximum_length": 255,
                "numeric_precision": None,
            },
        ],
        "indexes": [
            {
                "schemaname": "public",
                "tablename": "users",
                "indexname": "users_pkey",
                "indexdef": "CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id)",
            }
        ],
        "constraints": [
            {
                "constraint_schema": "public",
                "table_name": "users",
                "constraint_name": "users_pkey",
                "constraint_type": "PRIMARY KEY",
                "column_name": "id",
            }
        ],
    }


# ---------------------------------------------------------------------------
# Empty / no-change cases
# ---------------------------------------------------------------------------

class TestNoChange:
    def test_identical_snapshots_return_no_diffs(self, differ):
        snap = _base_snapshot()
        results = differ.diff(snap, snap)
        assert results == []

    def test_both_empty_return_no_diffs(self, differ):
        results = differ.diff({"columns": [], "indexes": [], "constraints": []},
                               {"columns": [], "indexes": [], "constraints": []})
        assert results == []


# ---------------------------------------------------------------------------
# Column changes
# ---------------------------------------------------------------------------

class TestColumnAdded:
    def test_detects_new_column(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["columns"].append({
            "table_schema": "public",
            "table_name": "users",
            "column_name": "created_at",
            "data_type": "timestamp without time zone",
            "is_nullable": "YES",
            "column_default": "now()",
            "character_maximum_length": None,
            "numeric_precision": None,
        })
        results = differ.diff(before, after)
        additions = [r for r in results if r.change_type == "column_added"]
        assert len(additions) == 1
        assert additions[0].object_name == "created_at"
        assert additions[0].object_type == "column"
        assert additions[0].before_state is None
        assert additions[0].after_state is not None

    def test_summary_mentions_column_and_table(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["columns"].append({
            "table_schema": "public",
            "table_name": "users",
            "column_name": "phone",
            "data_type": "text",
            "is_nullable": "YES",
            "column_default": None,
            "character_maximum_length": None,
            "numeric_precision": None,
        })
        results = differ.diff(before, after)
        additions = [r for r in results if r.change_type == "column_added"]
        assert "phone" in additions[0].human_readable_summary
        assert "users" in additions[0].human_readable_summary


class TestColumnDropped:
    def test_detects_dropped_column(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["columns"] = [c for c in after["columns"] if c["column_name"] != "email"]
        results = differ.diff(before, after)
        drops = [r for r in results if r.change_type == "column_dropped"]
        assert len(drops) == 1
        assert drops[0].object_name == "email"
        assert drops[0].after_state is None

    def test_dropped_column_schema_name(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["columns"] = [c for c in after["columns"] if c["column_name"] != "email"]
        results = differ.diff(before, after)
        drops = [r for r in results if r.change_type == "column_dropped"]
        assert drops[0].schema_name == "public"


class TestColumnModified:
    def _modify_column(self, snapshot, column_name, **overrides):
        snap = {
            "columns": [dict(c) for c in snapshot["columns"]],
            "indexes": snapshot["indexes"],
            "constraints": snapshot["constraints"],
        }
        for col in snap["columns"]:
            if col["column_name"] == column_name:
                col.update(overrides)
        return snap

    def test_detects_type_change(self, differ):
        before = _base_snapshot()
        after = self._modify_column(_base_snapshot(), "email", data_type="text")
        results = differ.diff(before, after)
        mods = [r for r in results if r.change_type == "column_modified"]
        assert len(mods) == 1
        assert mods[0].object_name == "email"

    def test_detects_nullable_change(self, differ):
        before = _base_snapshot()
        after = self._modify_column(_base_snapshot(), "email", is_nullable="NO")
        results = differ.diff(before, after)
        mods = [r for r in results if r.change_type == "column_modified"]
        assert len(mods) == 1
        assert "nullable" in mods[0].human_readable_summary

    def test_detects_default_change(self, differ):
        before = _base_snapshot()
        after = self._modify_column(_base_snapshot(), "email", column_default="'anon@example.com'")
        results = differ.diff(before, after)
        mods = [r for r in results if r.change_type == "column_modified"]
        assert len(mods) == 1

    def test_detects_length_change(self, differ):
        before = _base_snapshot()
        after = self._modify_column(_base_snapshot(), "email", character_maximum_length=512)
        results = differ.diff(before, after)
        mods = [r for r in results if r.change_type == "column_modified"]
        assert len(mods) == 1

    def test_modified_column_has_before_and_after(self, differ):
        before = _base_snapshot()
        after = self._modify_column(_base_snapshot(), "email", data_type="text")
        results = differ.diff(before, after)
        mods = [r for r in results if r.change_type == "column_modified"]
        assert mods[0].before_state is not None
        assert mods[0].after_state is not None
        assert mods[0].before_state["data_type"] == "character varying"
        assert mods[0].after_state["data_type"] == "text"


# ---------------------------------------------------------------------------
# Table changes
# ---------------------------------------------------------------------------

class TestTableChanges:
    def test_detects_new_table(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["columns"].append({
            "table_schema": "public",
            "table_name": "orders",
            "column_name": "id",
            "data_type": "integer",
            "is_nullable": "NO",
            "column_default": None,
            "character_maximum_length": None,
            "numeric_precision": 32,
        })
        results = differ.diff(before, after)
        created = [r for r in results if r.change_type == "table_added"]
        assert len(created) == 1
        assert created[0].object_name == "orders"
        assert "orders" in created[0].human_readable_summary

    def test_detects_dropped_table(self, differ):
        before = _base_snapshot()
        after = {"columns": [], "indexes": [], "constraints": []}
        results = differ.diff(before, after)
        dropped = [r for r in results if r.change_type == "table_dropped"]
        assert any(r.object_name == "users" for r in dropped)

    def test_dropped_table_before_state_set(self, differ):
        before = _base_snapshot()
        after = {"columns": [], "indexes": [], "constraints": []}
        results = differ.diff(before, after)
        dropped = [r for r in results if r.change_type == "table_dropped" and r.object_name == "users"]
        assert dropped[0].before_state is not None
        assert dropped[0].after_state is None


# ---------------------------------------------------------------------------
# Index changes
# ---------------------------------------------------------------------------

class TestIndexChanges:
    def test_detects_new_index(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["indexes"].append({
            "schemaname": "public",
            "tablename": "users",
            "indexname": "users_email_idx",
            "indexdef": "CREATE INDEX users_email_idx ON public.users USING btree (email)",
        })
        results = differ.diff(before, after)
        created = [r for r in results if r.change_type == "index_added"]
        assert len(created) == 1
        assert "users_email_idx" in created[0].object_name

    def test_detects_dropped_index(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["indexes"] = []
        results = differ.diff(before, after)
        dropped = [r for r in results if r.change_type == "index_dropped"]
        assert len(dropped) == 1
        assert "users_pkey" in dropped[0].object_name

    def test_index_diff_result_has_schema_name(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["indexes"] = []
        results = differ.diff(before, after)
        dropped = [r for r in results if r.change_type == "index_dropped"]
        assert dropped[0].schema_name == "public"


# ---------------------------------------------------------------------------
# Constraint changes
# ---------------------------------------------------------------------------

class TestConstraintChanges:
    def test_detects_new_constraint(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["constraints"].append({
            "constraint_schema": "public",
            "table_name": "users",
            "constraint_name": "users_email_unique",
            "constraint_type": "UNIQUE",
            "column_name": "email",
        })
        results = differ.diff(before, after)
        added = [r for r in results if r.change_type == "constraint_added"]
        assert len(added) == 1
        assert "users_email_unique" in added[0].object_name

    def test_detects_dropped_constraint(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["constraints"] = []
        results = differ.diff(before, after)
        dropped = [r for r in results if r.change_type == "constraint_dropped"]
        assert len(dropped) == 1
        assert "users_pkey" in dropped[0].object_name

    def test_constraint_drop_summary_mentions_type(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["constraints"] = []
        results = differ.diff(before, after)
        dropped = [r for r in results if r.change_type == "constraint_dropped"]
        assert "PRIMARY KEY" in dropped[0].human_readable_summary


# ---------------------------------------------------------------------------
# DiffResult model
# ---------------------------------------------------------------------------

class TestDiffResult:
    def test_diff_result_serializable(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["columns"].append({
            "table_schema": "public",
            "table_name": "users",
            "column_name": "bio",
            "data_type": "text",
            "is_nullable": "YES",
            "column_default": None,
            "character_maximum_length": None,
            "numeric_precision": None,
        })
        results = differ.diff(before, after)
        assert len(results) > 0
        payload = results[0].to_change_event_payload("org-123", "db-456")
        assert payload["org_id"] == "org-123"
        assert payload["database_id"] == "db-456"
        assert payload["change_type"] == "column_added"

    def test_diff_result_is_pydantic_model(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["indexes"] = []
        results = differ.diff(before, after)
        for r in results:
            assert isinstance(r, DiffResult)

    def test_diff_result_json_roundtrip(self, differ):
        before = _base_snapshot()
        after = _base_snapshot()
        after["columns"].append({
            "table_schema": "public",
            "table_name": "users",
            "column_name": "score",
            "data_type": "integer",
            "is_nullable": "YES",
            "column_default": "0",
            "character_maximum_length": None,
            "numeric_precision": 32,
        })
        results = differ.diff(before, after)
        for r in results:
            data = r.model_dump()
            assert isinstance(data, dict)
            assert "change_type" in data
