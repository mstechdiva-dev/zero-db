"""MySQL / MariaDB schema differ.

Detects changes between two MySQL information_schema snapshots.
"""

import os
import sys

_pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from engines.base_diff import BaseDiff  # noqa: E402
from models import DiffResult  # noqa: E402


class MySQLDiff(BaseDiff):
    """Diff two MySQL schema snapshots.

    Expected snapshot format (same as produced by mysql_listener.py):
    {
        "columns": [{"TABLE_SCHEMA", "TABLE_NAME", "COLUMN_NAME", "DATA_TYPE",
                     "IS_NULLABLE", "COLUMN_DEFAULT", "CHARACTER_MAXIMUM_LENGTH",
                     "NUMERIC_PRECISION"}, ...],
        "indexes": [{"TABLE_SCHEMA", "TABLE_NAME", "INDEX_NAME", "NON_UNIQUE",
                     "COLUMN_NAME", "SEQ_IN_INDEX"}, ...],
        "tables":  [{"TABLE_SCHEMA", "TABLE_NAME"}, ...],
    }
    """

    def diff(self, before: dict, after: dict) -> list[DiffResult]:
        results: list[DiffResult] = []
        results.extend(self._diff_tables(before, after))
        results.extend(self._diff_columns(before, after))
        results.extend(self._diff_indexes(before, after))
        return results

    @staticmethod
    def _col_key(col: dict) -> str:
        return f"{col['TABLE_SCHEMA']}.{col['TABLE_NAME']}.{col['COLUMN_NAME']}"

    @staticmethod
    def _table_key(t: dict) -> str:
        return f"{t['TABLE_SCHEMA']}.{t['TABLE_NAME']}"

    def _diff_tables(self, before: dict, after: dict) -> list[DiffResult]:
        before_set = {self._table_key(t) for t in before.get("tables", [])}
        after_set = {self._table_key(t) for t in after.get("tables", [])}
        results = []

        for table in after_set - before_set:
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

        for table in before_set - after_set:
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

    def _diff_columns(self, before: dict, after: dict) -> list[DiffResult]:
        before_map = {self._col_key(c): c for c in before.get("columns", [])}
        after_map = {self._col_key(c): c for c in after.get("columns", [])}
        results = []

        for key, col in after_map.items():
            if key not in before_map:
                results.append(
                    DiffResult(
                        change_type="column_added",
                        object_type="column",
                        object_name=col["COLUMN_NAME"],
                        schema_name=col["TABLE_SCHEMA"],
                        before_state=None,
                        after_state=col,
                        human_readable_summary=(
                            f"Column '{col['COLUMN_NAME']}' was added to "
                            f"'{col['TABLE_SCHEMA']}.{col['TABLE_NAME']}'."
                        ),
                    )
                )

        for key, col in before_map.items():
            if key not in after_map:
                results.append(
                    DiffResult(
                        change_type="column_dropped",
                        object_type="column",
                        object_name=col["COLUMN_NAME"],
                        schema_name=col["TABLE_SCHEMA"],
                        before_state=col,
                        after_state=None,
                        human_readable_summary=(
                            f"Column '{col['COLUMN_NAME']}' was dropped from "
                            f"'{col['TABLE_SCHEMA']}.{col['TABLE_NAME']}'."
                        ),
                    )
                )

        for key in before_map:
            if key in after_map and before_map[key] != after_map[key]:
                b, a = before_map[key], after_map[key]
                results.append(
                    DiffResult(
                        change_type="column_modified",
                        object_type="column",
                        object_name=b["COLUMN_NAME"],
                        schema_name=b["TABLE_SCHEMA"],
                        before_state=b,
                        after_state=a,
                        human_readable_summary=(
                            f"Column '{b['COLUMN_NAME']}' in "
                            f"'{b['TABLE_SCHEMA']}.{b['TABLE_NAME']}' was modified."
                        ),
                    )
                )

        return results

    def _diff_indexes(self, before: dict, after: dict) -> list[DiffResult]:
        def key(i: dict) -> str:
            return f"{i['TABLE_SCHEMA']}.{i['TABLE_NAME']}.{i['INDEX_NAME']}"

        before_map = {key(i): i for i in before.get("indexes", [])}
        after_map = {key(i): i for i in after.get("indexes", [])}
        results = []

        for k, idx in after_map.items():
            if k not in before_map:
                results.append(
                    DiffResult(
                        change_type="index_created",
                        object_type="index",
                        object_name=idx["INDEX_NAME"],
                        schema_name=idx["TABLE_SCHEMA"],
                        before_state=None,
                        after_state=idx,
                        human_readable_summary=(
                            f"Index '{idx['INDEX_NAME']}' was created on "
                            f"'{idx['TABLE_SCHEMA']}.{idx['TABLE_NAME']}'."
                        ),
                    )
                )

        for k, idx in before_map.items():
            if k not in after_map:
                results.append(
                    DiffResult(
                        change_type="index_dropped",
                        object_type="index",
                        object_name=idx["INDEX_NAME"],
                        schema_name=idx["TABLE_SCHEMA"],
                        before_state=idx,
                        after_state=None,
                        human_readable_summary=(
                            f"Index '{idx['INDEX_NAME']}' was dropped from "
                            f"'{idx['TABLE_SCHEMA']}.{idx['TABLE_NAME']}'."
                        ),
                    )
                )

        return results
