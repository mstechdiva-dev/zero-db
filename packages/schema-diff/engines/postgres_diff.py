"""PostgreSQL schema differ.

Detects changes between two PostgreSQL information_schema snapshots:
  - Column added / dropped / modified
  - Table added / dropped
  - Index added / dropped
  - Constraint added / dropped
  - Type changes, nullable changes, default value changes
"""

import os
import sys
from typing import Any

_pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from engines.base_diff import BaseDiff  # noqa: E402
from models import DiffResult  # noqa: E402


class PostgresDiff(BaseDiff):
    """Diff two PostgreSQL schema snapshots.

    Expected snapshot format (same as produced by postgres_listener.py):
    {
        "columns": [{"table_schema", "table_name", "column_name", "data_type",
                     "is_nullable", "column_default", "character_maximum_length",
                     "numeric_precision"}, ...],
        "indexes": [{"schemaname", "tablename", "indexname", "indexdef"}, ...],
        "constraints": [{"constraint_schema", "table_name", "constraint_name",
                         "constraint_type", "column_name"}, ...],
    }
    """

    def diff(self, before: dict, after: dict) -> list[DiffResult]:
        results: list[DiffResult] = []
        results.extend(self._diff_columns(before, after))
        results.extend(self._diff_tables(before, after))
        results.extend(self._diff_indexes(before, after))
        results.extend(self._diff_constraints(before, after))
        return results

    # ------------------------------------------------------------------
    # Column diffs
    # ------------------------------------------------------------------

    @staticmethod
    def _col_key(col: dict) -> str:
        return f"{col['table_schema']}.{col['table_name']}.{col['column_name']}"

    def _diff_columns(self, before: dict, after: dict) -> list[DiffResult]:
        results = []
        before_map = {self._col_key(c): c for c in before.get("columns", [])}
        after_map = {self._col_key(c): c for c in after.get("columns", [])}

        for key, col in after_map.items():
            if key not in before_map:
                results.append(
                    DiffResult(
                        change_type="column_added",
                        object_type="column",
                        object_name=col["column_name"],
                        schema_name=col["table_schema"],
                        before_state=None,
                        after_state=col,
                        human_readable_summary=(
                            f"Column '{col['column_name']}' was added to table "
                            f"'{col['table_schema']}.{col['table_name']}'."
                        ),
                    )
                )

        for key, col in before_map.items():
            if key not in after_map:
                results.append(
                    DiffResult(
                        change_type="column_dropped",
                        object_type="column",
                        object_name=col["column_name"],
                        schema_name=col["table_schema"],
                        before_state=col,
                        after_state=None,
                        human_readable_summary=(
                            f"Column '{col['column_name']}' was dropped from table "
                            f"'{col['table_schema']}.{col['table_name']}'."
                        ),
                    )
                )

        for key in before_map:
            if key not in after_map:
                continue
            b = before_map[key]
            a = after_map[key]
            if b != a:
                diffs = []
                if b.get("data_type") != a.get("data_type"):
                    diffs.append(
                        f"type changed from {b.get('data_type')} to {a.get('data_type')}"
                    )
                if b.get("is_nullable") != a.get("is_nullable"):
                    diffs.append(
                        f"nullable changed from {b.get('is_nullable')} to {a.get('is_nullable')}"
                    )
                if b.get("column_default") != a.get("column_default"):
                    diffs.append(
                        f"default changed from {b.get('column_default')!r} "
                        f"to {a.get('column_default')!r}"
                    )
                if b.get("character_maximum_length") != a.get("character_maximum_length"):
                    diffs.append(
                        f"max length changed from {b.get('character_maximum_length')} "
                        f"to {a.get('character_maximum_length')}"
                    )
                summary = (
                    f"Column '{b['column_name']}' in '{b['table_schema']}.{b['table_name']}' "
                    f"was modified: {'; '.join(diffs)}."
                ) if diffs else (
                    f"Column '{b['column_name']}' in '{b['table_schema']}.{b['table_name']}' changed."
                )
                results.append(
                    DiffResult(
                        change_type="column_modified",
                        object_type="column",
                        object_name=b["column_name"],
                        schema_name=b["table_schema"],
                        before_state=b,
                        after_state=a,
                        human_readable_summary=summary,
                    )
                )

        return results

    # ------------------------------------------------------------------
    # Table diffs (derived from column presence)
    # ------------------------------------------------------------------

    def _diff_tables(self, before: dict, after: dict) -> list[DiffResult]:
        before_tables = {
            f"{c['table_schema']}.{c['table_name']}"
            for c in before.get("columns", [])
        }
        after_tables = {
            f"{c['table_schema']}.{c['table_name']}"
            for c in after.get("columns", [])
        }

        results = []
        for table in after_tables - before_tables:
            schema, name = table.split(".", 1)
            results.append(
                DiffResult(
                    change_type="table_created",
                    object_type="table",
                    object_name=name,
                    schema_name=schema,
                    before_state=None,
                    after_state={"table": table},
                    human_readable_summary=f"Table '{table}' was created.",
                )
            )

        for table in before_tables - after_tables:
            schema, name = table.split(".", 1)
            results.append(
                DiffResult(
                    change_type="table_dropped",
                    object_type="table",
                    object_name=name,
                    schema_name=schema,
                    before_state={"table": table},
                    after_state=None,
                    human_readable_summary=f"Table '{table}' was dropped.",
                )
            )

        return results

    # ------------------------------------------------------------------
    # Index diffs
    # ------------------------------------------------------------------

    def _diff_indexes(self, before: dict, after: dict) -> list[DiffResult]:
        before_map = {i["indexname"]: i for i in before.get("indexes", [])}
        after_map = {i["indexname"]: i for i in after.get("indexes", [])}

        results = []
        for name, idx in after_map.items():
            if name not in before_map:
                results.append(
                    DiffResult(
                        change_type="index_created",
                        object_type="index",
                        object_name=name,
                        schema_name=idx.get("schemaname"),
                        before_state=None,
                        after_state=idx,
                        human_readable_summary=f"Index '{name}' was created on '{idx.get('tablename')}'.",
                    )
                )

        for name, idx in before_map.items():
            if name not in after_map:
                results.append(
                    DiffResult(
                        change_type="index_dropped",
                        object_type="index",
                        object_name=name,
                        schema_name=idx.get("schemaname"),
                        before_state=idx,
                        after_state=None,
                        human_readable_summary=f"Index '{name}' was dropped from '{idx.get('tablename')}'.",
                    )
                )

        return results

    # ------------------------------------------------------------------
    # Constraint diffs
    # ------------------------------------------------------------------

    def _diff_constraints(self, before: dict, after: dict) -> list[DiffResult]:
        before_map = {c["constraint_name"]: c for c in before.get("constraints", [])}
        after_map = {c["constraint_name"]: c for c in after.get("constraints", [])}

        results = []
        for name, con in after_map.items():
            if name not in before_map:
                results.append(
                    DiffResult(
                        change_type="constraint_added",
                        object_type="constraint",
                        object_name=name,
                        schema_name=con.get("constraint_schema"),
                        before_state=None,
                        after_state=con,
                        human_readable_summary=(
                            f"{con.get('constraint_type', 'Constraint')} '{name}' "
                            f"was added to '{con.get('table_name')}'."
                        ),
                    )
                )

        for name, con in before_map.items():
            if name not in after_map:
                results.append(
                    DiffResult(
                        change_type="constraint_dropped",
                        object_type="constraint",
                        object_name=name,
                        schema_name=con.get("constraint_schema"),
                        before_state=con,
                        after_state=None,
                        human_readable_summary=(
                            f"{con.get('constraint_type', 'Constraint')} '{name}' "
                            f"was dropped from '{con.get('table_name')}'."
                        ),
                    )
                )

        return results
