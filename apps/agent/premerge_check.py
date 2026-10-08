"""Pre-merge check: read SQL migration files and flag risky schema changes.

Uses the same risk levels as Zero (zero/risk_scorer.py). It reads the SQL text only:
no database connection, no Claude call, nothing leaves the machine.

    python premerge_check.py migrations/009_cleanup.sql [more.sql ...]
    python premerge_check.py --fail-on critical file.sql
    cat file.sql | python premerge_check.py -

Exit code is 1 if anything is at or above --fail-on (default: high), else 0.
"""

import argparse
import re
import sys
from dataclasses import dataclass

from zero.risk_scorer import next_action, score

LEVELS = ["low", "medium", "high", "critical"]


@dataclass
class Finding:
    file: str
    line: int
    risk: str
    what: str


def _strip_comments(sql: str) -> str:
    """Remove -- and /* */ comments but keep newlines so line numbers still match."""
    sql = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), sql, flags=re.S)
    return re.sub(r"--[^\n]*", "", sql)


def _split_top_level(text: str, sep: str) -> list[str]:
    """Split on `sep` outside parentheses and quotes."""
    parts, depth, quote, buf = [], 0, "", []
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            continue
        if ch in "'\"":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf))
    return parts


def _name(raw: str) -> str:
    return raw.strip().strip('"`').split(".")[-1].strip('"`')


IDENT = r'((?:"[^"]+"|`[^`]+`|[\w$]+)(?:\.(?:"[^"]+"|`[^`]+`|[\w$]+))?)'
IF_EXISTS = r"(?:IF\s+EXISTS\s+)?"


def _constraint_type(name: str) -> str:
    n = name.lower()
    if n.endswith(("_pkey", "_pk")):
        return "PRIMARY KEY"
    if n.endswith(("_fkey", "_fk")):
        return "FOREIGN KEY"
    if n.endswith(("_key", "_unique", "_uq")):
        return "UNIQUE"
    if n.endswith(("_check", "_ck")):
        return "CHECK"
    return ""


def _alter_action(table: str, action: str):
    """Return (risk, description) for one ALTER TABLE action, or None to ignore it."""
    a = " ".join(action.split())
    u = a.upper()

    m = re.match(rf"DROP\s+(?:COLUMN\s+)?{IF_EXISTS}{IDENT}", a, re.I)
    if m and not u.startswith(("DROP CONSTRAINT", "DROP DEFAULT", "DROP NOT NULL", "DROP IDENTITY")):
        return score("column_dropped", "column"), f"DROP COLUMN {_name(m.group(1))} on {table}"

    m = re.match(rf"DROP\s+CONSTRAINT\s+{IF_EXISTS}{IDENT}", a, re.I)
    if m:
        name = _name(m.group(1))
        ctype = _constraint_type(name)
        risk = score("constraint_dropped", "constraint", before_state={"constraint_type": ctype})
        return risk, f"DROP CONSTRAINT {name} on {table}"

    m = re.match(rf"ALTER\s+(?:COLUMN\s+)?{IDENT}\s+SET\s+NOT\s+NULL", a, re.I)
    if m:
        risk = score("column_modified", "column",
                     before_state={"is_nullable": "YES"}, after_state={"is_nullable": "NO"})
        return risk, f"SET NOT NULL on {table}.{_name(m.group(1))} (fails or blocks if any row is NULL)"

    m = re.match(rf"ALTER\s+(?:COLUMN\s+)?{IDENT}\s+DROP\s+NOT\s+NULL", a, re.I)
    if m:
        risk = score("column_modified", "column",
                     before_state={"is_nullable": "NO"}, after_state={"is_nullable": "YES"})
        return risk, f"DROP NOT NULL on {table}.{_name(m.group(1))} (code may assume it is never empty)"

    m = re.match(rf"ALTER\s+(?:COLUMN\s+)?{IDENT}\s+(?:SET\s+DATA\s+)?TYPE\s+(.+)", a, re.I)
    if m:
        # We can't see the old type from SQL alone, so this stays at "review".
        risk = score("column_modified", "column")
        return risk, f"type change on {table}.{_name(m.group(1))} to {m.group(2).strip()} (check it can't lose data)"

    m = re.match(rf"RENAME\s+(?:COLUMN\s+)?{IDENT}\s+TO\s+{IDENT}", a, re.I)
    if m and not u.startswith("RENAME TO"):
        # Anything still reading the old name breaks, same as a drop.
        return score("column_dropped", "column"), (
            f"RENAME COLUMN {_name(m.group(1))} to {_name(m.group(2))} on {table}")

    m = re.match(rf"RENAME\s+TO\s+{IDENT}", a, re.I)
    if m:
        return score("table_dropped", "table"), f"RENAME TABLE {table} to {_name(m.group(1))}"

    m = re.match(rf"ADD\s+(?:COLUMN\s+)?(?:IF\s+NOT\s+EXISTS\s+)?{IDENT}\s+(.*)", a, re.I)
    if m and not u.startswith(("ADD CONSTRAINT", "ADD PRIMARY", "ADD FOREIGN", "ADD UNIQUE", "ADD CHECK")):
        col, rest = _name(m.group(1)), m.group(2).upper()
        if "NOT NULL" in rest and "DEFAULT" not in rest:
            risk = score("column_modified", "column",
                         before_state={"is_nullable": "YES"}, after_state={"is_nullable": "NO"})
            return risk, f"ADD COLUMN {col} NOT NULL with no default on {table} (fails if the table has rows)"
        return score("column_added", "column"), f"ADD COLUMN {col} on {table}"

    if re.match(r"ADD\s+(?:CONSTRAINT\s+\S+\s+)?PRIMARY\s+KEY", a, re.I):
        return score("constraint_added", "constraint", after_state={"constraint_type": "PRIMARY KEY"}), (
            f"ADD PRIMARY KEY on {table}")
    if re.match(r"ADD\s+(?:CONSTRAINT|FOREIGN|UNIQUE|CHECK)", a, re.I):
        return score("constraint_added", "constraint"), f"ADD CONSTRAINT on {table}"
    return None


def check_sql(sql: str, filename: str = "<stdin>") -> list[Finding]:
    text = _strip_comments(sql)
    findings: list[Finding] = []
    pos = 0
    for stmt in _split_top_level(text, ";"):
        line = text.count("\n", 0, pos) + 1 + (len(stmt) - len(stmt.lstrip("\n")))
        pos += len(stmt) + 1
        s = " ".join(stmt.split())
        if not s:
            continue

        m = re.match(rf"DROP\s+TABLE\s+{IF_EXISTS}(.+)", s, re.I)
        if m:
            for t in _split_top_level(re.sub(r"\s+(CASCADE|RESTRICT)\s*$", "", m.group(1), flags=re.I), ","):
                findings.append(Finding(filename, line, score("table_dropped", "table"),
                                        f"DROP TABLE {_name(t)}"))
            continue

        m = re.match(rf"DROP\s+INDEX\s+(?:CONCURRENTLY\s+)?{IF_EXISTS}{IDENT}", s, re.I)
        if m:
            findings.append(Finding(filename, line, score("index_dropped", "index"),
                                    f"DROP INDEX {_name(m.group(1))}"))
            continue

        m = re.match(rf"CREATE\s+(?:UNLOGGED\s+|TEMP(?:ORARY)?\s+)?TABLE\s+{IF_EXISTS.replace('EXISTS', 'NOT EXISTS')}{IDENT}", s, re.I)
        if m:
            findings.append(Finding(filename, line, score("table_created", "table"),
                                    f"CREATE TABLE {_name(m.group(1))}"))
            continue

        if re.match(r"CREATE\s+(?:UNIQUE\s+)?INDEX", s, re.I):
            findings.append(Finding(filename, line, score("index_created", "index"), "CREATE INDEX"))
            continue

        m = re.match(rf"ALTER\s+TABLE\s+(?:ONLY\s+)?(?:IF\s+EXISTS\s+)?{IDENT}\s+(.*)", s, re.I)
        if m:
            table = _name(m.group(1))
            for action in _split_top_level(m.group(2), ","):
                hit = _alter_action(table, action)
                if hit:
                    findings.append(Finding(filename, line, hit[0], hit[1]))
    return findings


def format_findings(findings: list[Finding]) -> str:
    if not findings:
        return "No schema changes found."
    out = []
    for f in sorted(findings, key=lambda f: (-LEVELS.index(f.risk), f.file, f.line)):
        out.append(f"{f.risk.upper():8} {f.file}:{f.line}  {f.what}\n         {next_action(f.risk)}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Flag risky schema changes in SQL migration files.")
    ap.add_argument("files", nargs="*", help="SQL files, or - for stdin")
    ap.add_argument("--fail-on", choices=LEVELS, default="high",
                    help="exit 1 if any change is at or above this level (default: high)")
    args = ap.parse_args(argv)

    findings: list[Finding] = []
    for path in args.files or ["-"]:
        if path == "-":
            findings += check_sql(sys.stdin.read(), "<stdin>")
        else:
            with open(path, encoding="utf-8") as fh:
                findings += check_sql(fh.read(), path)

    print(format_findings(findings))
    worst = max((LEVELS.index(f.risk) for f in findings), default=-1)
    if worst >= LEVELS.index(args.fail_on):
        print(f"\nBlocked: found a change at or above '{args.fail_on}'.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
