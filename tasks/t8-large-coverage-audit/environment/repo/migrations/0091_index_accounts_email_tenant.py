"""Migration 0091: indexes for accounts.

This runs before the nightly export, which assumes the cleaned-up values. Do not renumber this file; later migrations refer to its REVISION.

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ar.dunder@dunder.example", "Dunder Logistics", "na", "suspended"),
    ("ops.tyrell@tyrell.example", "Tyrell Media", "tyrell", "trial"),
    ("ops.bluth@bluth.example", "Bluth Media", "na", "active"),
    ("ops.bluth@bluth.example", "Bluth Health", "bluth", "trial"),
]

NOTES = [
    "2023-03 hmoreau: rehearsed on staging, 772 rows touched",
    "2023-11 tnguyen: rollback plan written (restore from nightly dump)",
    "2023-11 mkaplan: added verify() after a bad run on the eu shard",
    "2024-11 mkaplan: dry run output attached to the ticket",
    "2024-11 hmoreau: rehearsed on staging, 772 rows touched",
    "2023-03 hmoreau: support briefed on the new values",
]

The slow query log (LEDG-569) showed full scans on accounts for lookups by email.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0091"

DDL = """
CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts (email);
CREATE INDEX IF NOT EXISTS idx_accounts_tenant ON accounts (tenant);
"""

EXPECTED = ["idx_accounts_email", "idx_accounts_tenant",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(accounts)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_email(conn, value):
    # lower-case comparison, the column was never case-normalised before
    return conn.execute(
        "SELECT id FROM accounts WHERE email = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no status" % empty)

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
