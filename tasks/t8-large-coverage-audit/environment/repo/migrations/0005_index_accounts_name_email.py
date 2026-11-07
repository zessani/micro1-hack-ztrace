"""Migration 0005: indexes for accounts.

This runs before the nightly export, which assumes the cleaned-up values. Support kept hitting this in the dashboard, so we are fixing it at the data layer.

The slow query log (BILL-434) showed full scans on accounts for lookups by name.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0005"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("billing.initech@initech.example", "Initech Labs", "apac", "suspended"),
    ("ap.oscorp@oscorp.example", "Oscorp Partners", "na", "active"),
]

NOTES = [
    "2025-06 vkrause: added verify() after a bad run on the eu shard",
    "2023-06 vkrause: rollback plan written (restore from nightly dump)",
    "2023-11 vkrause: renamed helper to match the support console",
    "2024-05 vkrause: widened batch size after load test",
    "2025-06 jdiaz: tightened the match to avoid touching enterprise tenants",
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
    # NULL and empty string are both treated as 'missing' on purpose
    return conn.execute(
        "SELECT id FROM accounts WHERE name = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE tenant IS NULL OR tenant = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no tenant" % empty)

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
