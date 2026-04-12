"""Redis key pattern differ.

Detects changes between two Redis namespace snapshots:
  - New key patterns (namespace level, not individual keys)
  - Dropped key patterns
  - TTL policy changes
  - Data type changes at pattern level
"""

import os
import sys

_pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from engines.base_diff import BaseDiff  # noqa: E402
from models import DiffResult  # noqa: E402


class RedisDiff(BaseDiff):
    """Diff two Redis namespace snapshots.

    Expected snapshot format (same as produced by redis_listener.py):
    {
        "namespaces": {
            "<namespace>": {
                "type": "<redis_type>",
                "has_ttl": <bool>,
                "sample_key": "<key>"
            },
            ...
        }
    }
    """

    def diff(self, before: dict, after: dict) -> list[DiffResult]:
        results: list[DiffResult] = []
        before_ns = before.get("namespaces", {})
        after_ns = after.get("namespaces", {})

        for ns, info in after_ns.items():
            if ns not in before_ns:
                results.append(
                    DiffResult(
                        change_type="key_pattern_added",
                        object_type="key_namespace",
                        object_name=ns,
                        schema_name=None,
                        before_state=None,
                        after_state=info,
                        human_readable_summary=(
                            f"New key namespace '{ns}' appeared (type: {info.get('type', 'unknown')})."
                        ),
                    )
                )
            else:
                before_info = before_ns[ns]
                if before_info.get("type") != info.get("type"):
                    results.append(
                        DiffResult(
                            change_type="key_type_changed",
                            object_type="key_namespace",
                            object_name=ns,
                            schema_name=None,
                            before_state=before_info,
                            after_state=info,
                            human_readable_summary=(
                                f"Key namespace '{ns}' changed type from "
                                f"'{before_info.get('type')}' to '{info.get('type')}'."
                            ),
                        )
                    )
                elif before_info.get("has_ttl") != info.get("has_ttl"):
                    results.append(
                        DiffResult(
                            change_type="ttl_policy_changed",
                            object_type="key_namespace",
                            object_name=ns,
                            schema_name=None,
                            before_state=before_info,
                            after_state=info,
                            human_readable_summary=(
                                f"TTL policy for key namespace '{ns}' changed: "
                                f"has_ttl {before_info.get('has_ttl')} → {info.get('has_ttl')}."
                            ),
                        )
                    )

        for ns, info in before_ns.items():
            if ns not in after_ns:
                results.append(
                    DiffResult(
                        change_type="key_pattern_dropped",
                        object_type="key_namespace",
                        object_name=ns,
                        schema_name=None,
                        before_state=info,
                        after_state=None,
                        human_readable_summary=(
                            f"Key namespace '{ns}' disappeared from the keyspace."
                        ),
                    )
                )

        return results
