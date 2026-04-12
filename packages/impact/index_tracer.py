"""Index tracer — identifies indexes affected by a schema change.

Examines the change event to determine which indexes are impacted and
whether the change could cause query performance regressions.
"""

from typing import Optional


class IndexTracer:
    """Traces which indexes are affected by a schema change."""

    def trace(
        self,
        change_type: str,
        object_type: str,
        object_name: str,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
    ) -> list[str]:
        """Return a list of affected index names or descriptions.

        Parameters
        ----------
        change_type:
            The type of schema change.
        object_type:
            The type of object changed.
        object_name:
            The name of the changed object.
        before_state, after_state:
            Before/after snapshots for context.

        Returns
        -------
        list[str]
            Index names or descriptive strings about index impact.
        """
        ct = change_type.lower()
        ot = object_type.lower()

        if ot == "index":
            return self._trace_direct_index(ct, object_name, before_state, after_state)

        if ot == "column":
            return self._trace_column_index_impact(ct, object_name, before_state, after_state)

        if ot == "table":
            return self._trace_table_index_impact(ct, object_name)

        if ot == "constraint":
            return self._trace_constraint_index(ct, object_name, before_state, after_state)

        return []

    @staticmethod
    def _trace_direct_index(
        change_type: str,
        index_name: str,
        before: Optional[dict],
        after: Optional[dict],
    ) -> list[str]:
        if change_type == "index_dropped":
            table = ""
            if before and "tablename" in before:
                table = before["tablename"]
            elif before and "TABLE_NAME" in before:
                table = before["TABLE_NAME"]
            result = [index_name]
            if table:
                result.append(
                    f"Queries on '{table}' that previously used '{index_name}' may scan the full table"
                )
            return result

        if change_type == "index_created":
            return [index_name]

        return [index_name]

    @staticmethod
    def _trace_column_index_impact(
        change_type: str,
        column_name: str,
        before: Optional[dict],
        after: Optional[dict],
    ) -> list[str]:
        """Dropping or modifying a column may invalidate indexes that include it."""
        if change_type in ("column_dropped", "column_modified"):
            table = ""
            for state in (before, after):
                if state and "table_name" in state:
                    table = state["table_name"]
                    break
                if state and "TABLE_NAME" in state:
                    table = state["TABLE_NAME"]
                    break
            if table:
                return [
                    f"Any composite index on '{table}' that includes column '{column_name}'"
                ]
        return []

    @staticmethod
    def _trace_table_index_impact(change_type: str, table_name: str) -> list[str]:
        if change_type == "table_dropped":
            return [f"All indexes on '{table_name}' (dropped with the table)"]
        return []

    @staticmethod
    def _trace_constraint_index(
        change_type: str,
        constraint_name: str,
        before: Optional[dict],
        after: Optional[dict],
    ) -> list[str]:
        """PRIMARY KEY and UNIQUE constraints are backed by indexes."""
        con_type = ""
        for state in (before, after):
            if state and "constraint_type" in state:
                con_type = str(state["constraint_type"]).upper()
                break

        if con_type in ("PRIMARY KEY", "UNIQUE"):
            return [f"Implicit index backing constraint '{constraint_name}'"]

        return []
