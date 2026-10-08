"""Pre-merge check reads migration SQL and flags risky changes."""

import premerge_check as pm


def risks(sql):
    return [(f.risk, f.what) for f in pm.check_sql(sql)]


def test_drop_column_is_high():
    assert risks("ALTER TABLE users DROP COLUMN legacy_email;")[0][0] == "high"


def test_drop_table_is_critical():
    assert risks("DROP TABLE IF EXISTS orders CASCADE;") == [("critical", "DROP TABLE orders")]


def test_additive_changes_are_low():
    sql = """
    CREATE TABLE audit (id int);
    CREATE INDEX idx_a ON audit (id);
    ALTER TABLE users ADD COLUMN nickname text;
    """
    assert {r for r, _ in risks(sql)} == {"low"}


def test_not_null_without_default_is_high():
    assert risks("ALTER TABLE users ADD COLUMN age int NOT NULL;")[0][0] == "high"
    assert risks("ALTER TABLE users ADD COLUMN age int NOT NULL DEFAULT 0;")[0][0] == "low"
    assert risks("ALTER TABLE users ALTER COLUMN email SET NOT NULL;")[0][0] == "high"


def test_constraint_drops_by_name():
    assert risks("ALTER TABLE a DROP CONSTRAINT a_pkey;")[0][0] == "critical"
    assert risks("ALTER TABLE a DROP CONSTRAINT a_b_fkey;")[0][0] == "critical"
    assert risks("ALTER TABLE a DROP CONSTRAINT a_email_key;")[0][0] == "high"
    assert risks("ALTER TABLE a DROP CONSTRAINT something;")[0][0] == "medium"


def test_rename_and_type_change():
    assert risks("ALTER TABLE a RENAME COLUMN x TO y;")[0][0] == "high"
    assert risks("ALTER TABLE a RENAME TO b;")[0][0] == "critical"
    assert risks("ALTER TABLE a ALTER COLUMN x TYPE bigint;")[0][0] == "medium"


def test_multiple_actions_in_one_statement():
    found = risks("ALTER TABLE a ADD COLUMN z int, DROP COLUMN old;")
    assert [r for r, _ in found] == ["low", "high"]


def test_comments_and_drop_not_null_ignored_properly():
    sql = "-- DROP TABLE nope;\n/* DROP TABLE nope2; */\nALTER TABLE a ALTER COLUMN x DROP NOT NULL;"
    assert risks(sql)[0][0] == "medium"
    assert all("nope" not in w for _, w in risks(sql))


def test_line_numbers():
    f = pm.check_sql("CREATE TABLE t (id int);\n\n\nDROP TABLE t;")
    assert [(x.line, x.risk) for x in f] == [(1, "low"), (4, "critical")]


def test_exit_codes(tmp_path):
    bad = tmp_path / "bad.sql"
    bad.write_text("ALTER TABLE users DROP COLUMN legacy_email;")
    ok = tmp_path / "ok.sql"
    ok.write_text("ALTER TABLE users ADD COLUMN nickname text;")
    assert pm.main([str(bad)]) == 1
    assert pm.main([str(ok)]) == 0
    assert pm.main(["--fail-on", "critical", str(bad)]) == 0
    assert pm.main(["--fail-on", "critical", str(bad), str(tmp_path / "ok.sql")]) == 0


def test_every_repo_migration_runs():
    import glob, os
    root = os.path.join(os.path.dirname(__file__), "..", "..", "..", "supabase", "migrations", "*.sql")
    for path in glob.glob(root):
        pm.check_sql(open(path, encoding="utf-8").read(), path)  # must not crash


def test_add_column_if_not_exists():
    found = pm.check_sql("ALTER TABLE a ADD COLUMN IF NOT EXISTS z int;")
    assert [(f.risk, f.what) for f in found] == [("low", "ADD COLUMN z on a")]
