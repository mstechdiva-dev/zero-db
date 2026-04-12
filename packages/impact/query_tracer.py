"""Query tracer — identifies queries and API endpoints affected by a schema change.

This module uses heuristic analysis to identify which queries are likely
affected by a schema change. It examines the change type and object name
to produce a list of patterns the team should search for in their codebase.
"""

from typing import Optional


class QueryTracer:
    """Traces which query patterns are affected by a schema change."""

    def trace(
        self,
        change_type: str,
        object_type: str,
        object_name: str,
        schema_name: Optional[str] = None,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
    ) -> list[str]:
        """Return a list of query patterns likely affected by this change.

        Parameters
        ----------
        change_type:
            The type of schema change (e.g. 'column_dropped').
        object_type:
            The type of object changed (e.g. 'column', 'table').
        object_name:
            The name of the changed object.
        schema_name:
            The schema (e.g. 'public') the object belongs to.
        before_state, after_state:
            Before/after snapshots for context.

        Returns
        -------
        list[str]
            Human-readable patterns/descriptions the team should search for.
        """
        ct = change_type.lower()
        ot = object_type.lower()
        name = object_name

        if ot == "column":
            table_name = self._extract_table(before_state, after_state)
            return self._trace_column(ct, name, table_name)

        if ot == "table":
            return self._trace_table(ct, name, schema_name)

        if ot == "index":
            table_name = self._extract_index_table(before_state, after_state)
            return self._trace_index(ct, name, table_name)

        if ot == "constraint":
            return self._trace_constraint(ct, name, before_state, after_state)

        if ot == "collection":
            return [f"Any query referencing collection '{name}'"]

        if ot == "key_namespace":
            return [f"Any code using Redis keys matching '{name}:*'"]

        return [f"Queries referencing '{name}'"]

    @staticmethod
    def _extract_table(before: Optional[dict], after: Optional[dict]) -> str:
        for state in (after, before):
            if state and "table_name" in state:
                return state["table_name"]
            if state and "TABLE_NAME" in state:
                return state["TABLE_NAME"]
        return "unknown_table"

    @staticmethod
    def _extract_index_table(before: Optional[dict], after: Optional[dict]) -> str:
        for state in (after, before):
            if state and "tablename" in state:
                return state["tablename"]
            if state and "TABLE_NAME" in state:
                return state["TABLE_NAME"]
        return "unknown_table"

    @staticmethod
    def _trace_column(change_type: str, column_name: str, table_name: str) -> list[str]:
        patterns = [
            f"SELECT statements referencing '{column_name}' on '{table_name}'",
            f"INSERT/UPDATE statements writing to '{column_name}'",
            f"ORM models mapping '{table_name}.{column_name}'",
        ]
        if change_type == "column_dropped":
            patterns.append(f"Any code using '{table_name}.{column_name}' — this column no longer exists")
        elif change_type == "column_modified":
            patterns.append(
                f"Type-sensitive operations on '{column_name}' that may fail after the type change"
            )
        return patterns

    @staticmethod
    def _trace_table(change_type: str, table_name: str, schema_name: Optional[str]) -> list[str]:
        full_name = f"{schema_name}.{table_name}" if schema_name else table_name
        patterns = [
            f"All queries referencing table '{full_name}'",
            f"ORM models mapped to '{full_name}'",
            f"Foreign keys referencing '{full_name}'",
        ]
        if change_type == "table_dropped":
            patterns.append(f"Any code touching '{full_name}' — this table no longer exists")
        return patterns

    @staticmethod
    def _trace_index(change_type: str, index_name: str, table_name: str) -> list[str]:
        patterns = [
            f"Queries on '{table_name}' that relied on index '{index_name}' for performance",
        ]
        if change_type == "index_dropped":
            patterns.append(
                f"High-frequency queries on '{table_name}' may now perform full table scans"
            )
        return patterns

    @staticmethod
    def _trace_constraint(
        change_type: str,
        constraint_name: str,
        before: Optional[dict],
        after: Optional[dict],
    ) -> list[str]:
        con_type = ""
        for state in (before, after):
            if state and "constraint_type" in state:
                con_type = state["constraint_type"]
                break

        table_name = ""
        for state in (before, after):
            if state and "table_name" in state:
                table_name = state["table_name"]
                break

        patterns = [f"Writes to '{table_name}' that may violate the {con_type} constraint '{constraint_name}'"]
        if change_type == "constraint_dropped" and con_type in ("FOREIGN KEY", "PRIMARY KEY"):
            patterns.append(
                f"Code relying on referential integrity enforced by '{constraint_name}'"
            )
        return patterns
