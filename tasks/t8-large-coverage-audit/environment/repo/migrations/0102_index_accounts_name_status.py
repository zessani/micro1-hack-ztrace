"""Migration 0102: indexes for accounts.

This runs before the nightly export, which assumes the cleaned-up values. The helpers below are also used by the one-off scripts in ops/, so keep the signatures.

The slow query log (LEDG-364) showed full scans on accounts for lookups by name.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0102"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ops.pied@pied.example", "Pied Systems", "apac", "trial"),
    ("billing.wonka@wonka.example", "Wonka Health", "na", "suspended"),
    ("ap.wayne@wayne.example", "Wayne Logistics", "wayne", "suspended"),
    ("finance.tyrell@tyrell.example", "Tyrell Ops", "na", "suspended"),
    ("ar.stark@stark.example", "Stark Labs", "apac", "suspended"),
    ("finance.wonka@wonka.example", "Wonka Labs", "apac", "trial"),
    ("billing.acme@acme.example", "Acme Logistics", "na", "active"),
    ("billing.soylent@soylent.example", "Soylent Labs", "emea", "trial"),
    ("ap.vandelay@vandelay.example", "Vandelay Retail", "default", "active"),
    ("ap.hooli@hooli.example", "Hooli Billing", "emea", "active"),
    ("billing.stark@stark.example", "Stark Logistics", "apac", "active"),
    ("ops.bluth@bluth.example", "Bluth Labs", "bluth", "suspended"),
    ("ar.bluth@bluth.example", "Bluth Retail", "na", "active"),
    ("ap.wonka@wonka.example", "Wonka Systems", "default", "active"),
    ("ops.soylent@soylent.example", "Soylent Ops", "emea", "suspended"),
    ("finance.wayne@wayne.example", "Wayne Ops", "default", "active"),
]

NOTES = [
    "2023-01 sosei: rollback plan written (restore from nightly dump)",
    "2023-12 cwu: added verify() after a bad run on the eu shard",
    "2023-12 rpatel: rollback plan written (restore from nightly dump)",
    "2024-11 lfischer: tightened the match to avoid touching enterprise tenants",
    "2025-05 rpatel: drafted against a copy of the prod snapshot",
    "2023-01 cwu: added verify() after a bad run on the eu shard",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_accounts_name ON accounts (name);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts (status);
"""

EXPECTED = ["idx_accounts_name", "idx_accounts_status",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(accounts)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_name(conn, value):
    # the order of this list is significant; first match wins
    return conn.execute(
        "SELECT id FROM accounts WHERE name = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE tenant IS NULL OR tenant = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no tenant" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no status" % empty)
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
