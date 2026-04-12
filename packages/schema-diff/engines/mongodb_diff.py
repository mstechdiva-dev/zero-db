"""MongoDB schema differ.

Detects changes between two MongoDB snapshots:
  - Collection added / dropped
  - Index added / dropped
  - Validation schema changes
"""

import os
import sys

_pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from engines.base_diff import BaseDiff  # noqa: E402
from models import DiffResult  # noqa: E402


class MongoDBDiff(BaseDiff):
    """Diff two MongoDB schema snapshots.

    Expected snapshot format (same as produced by mongodb_listener.py):
    {
        "collections": {
            "<collection_name>": {
                "indexes": {"<index_name>": {<index_info>}, ...},
                "validator": {<json_schema>}  # optional
            },
            ...
        }
    }
    """

    def diff(self, before: dict, after: dict) -> list[DiffResult]:
        results: list[DiffResult] = []
        before_cols = before.get("collections", {})
        after_cols = after.get("collections", {})

        # Collections added
        for name in after_cols:
            if name not in before_cols:
                results.append(
                    DiffResult(
                        change_type="collection_created",
                        object_type="collection",
                        object_name=name,
                        schema_name=None,
                        before_state=None,
                        after_state=after_cols[name],
                        human_readable_summary=f"Collection '{name}' was created.",
                    )
                )

        # Collections dropped
        for name in before_cols:
            if name not in after_cols:
                results.append(
                    DiffResult(
                        change_type="collection_dropped",
                        object_type="collection",
                        object_name=name,
                        schema_name=None,
                        before_state=before_cols[name],
                        after_state=None,
                        human_readable_summary=f"Collection '{name}' was dropped.",
                    )
                )

        # Indexes within existing collections
        for name in before_cols:
            if name not in after_cols:
                continue
            before_idx = before_cols[name].get("indexes", {})
            after_idx = after_cols[name].get("indexes", {})

            for idx_name in after_idx:
                if idx_name not in before_idx:
                    results.append(
                        DiffResult(
                            change_type="index_created",
                            object_type="index",
                            object_name=idx_name,
                            schema_name=name,
                            before_state=None,
                            after_state=after_idx[idx_name],
                            human_readable_summary=(
                                f"Index '{idx_name}' was created on collection '{name}'."
                            ),
                        )
                    )

            for idx_name in before_idx:
                if idx_name not in after_idx:
                    results.append(
                        DiffResult(
                            change_type="index_dropped",
                            object_type="index",
                            object_name=idx_name,
                            schema_name=name,
                            before_state=before_idx[idx_name],
                            after_state=None,
                            human_readable_summary=(
                                f"Index '{idx_name}' was dropped from collection '{name}'."
                            ),
                        )
                    )

            # Validation schema changes
            before_validator = before_cols[name].get("validator")
            after_validator = after_cols[name].get("validator")
            if before_validator != after_validator:
                results.append(
                    DiffResult(
                        change_type="schema_change",
                        object_type="validator",
                        object_name=name,
                        schema_name=None,
                        before_state=before_validator,
                        after_state=after_validator,
                        human_readable_summary=(
                            f"Validation schema for collection '{name}' was modified."
                        ),
                    )
                )

        return results
