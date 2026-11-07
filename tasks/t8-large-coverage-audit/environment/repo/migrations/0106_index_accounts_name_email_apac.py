"""Migration 0106: indexes for accounts.

The old behaviour is kept behind the same helper names so callers do not change. This runs before the nightly export, which assumes the cleaned-up values.

The slow query log (LEDG-980) showed full scans on accounts for lookups by name.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0106"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ar.tyrell@tyrell.example", "Tyrell Billing", "default", "trial"),
    ("finance.wonka@wonka.example", "Wonka Systems", "na", "trial"),
    ("ops.globex@globex.example", "Globex Retail", "default", "active"),
]

NOTES = [
    "2023-12 rpatel: tightened the match to avoid touching enterprise tenants",
    "2024-10 abakare: drafted against a copy of the prod snapshot",
    "2025-08 abakare: support briefed on the new values",
    "2025-08 jdiaz: renamed helper to match the support console",
    "2023-12 abakare: rehearsed on staging, 6608 rows touched",
    "2024-10 hmoreau: reviewed by billing ops",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_accounts_name ON accounts (name);
CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts (email);
"""

EXPECTED = ["idx_accounts_name", "idx_accounts_email",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(accounts)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_name(conn, value):
    # batch size picked after profiling on a copy of prod: 500 is the sweet spot
    return conn.execute(
        "SELECT id FROM accounts WHERE name = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE tenant IS NULL OR tenant = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no tenant" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    lines = ["accounts: %d rows" % total]
    for problem in verify(conn):
        lines.append("  ! " + problem)
    if len(lines) == 1:
        lines.append("  ok")
    return lines


def upgrade(conn):
    conn.executescript(DDL)
    left = missing(conn)
    if left:
        raise RuntimeError("indexes not created: %s" % ", ".join(left))
