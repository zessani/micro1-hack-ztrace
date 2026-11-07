"""Migration 0059: indexes for accounts.

We deliberately leave rows we do not recognise alone and report them afterwards. The change is idempotent: rerunning on an already migrated database is a no-op.

The slow query log (SUP-649) showed full scans on accounts for lookups by name.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0059"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ops.massive@massive.example", "Massive Systems", "emea", "suspended"),
    ("ops.sterling@sterling.example", "Sterling Systems", "emea", "trial"),
    ("ap.bluth@bluth.example", "Bluth Media", "apac", "suspended"),
    ("ops.vandelay@vandelay.example", "Vandelay Retail", "vandelay", "suspended"),
    ("ops.soylent@soylent.example", "Soylent Logistics", "default", "active"),
    ("ap.globex@globex.example", "Globex Partners", "emea", "trial"),
]

NOTES = [
    "2023-12 tnguyen: support briefed on the new values",
    "2023-09 cwu: reviewed by billing ops",
    "2023-12 cwu: drafted against a copy of the prod snapshot",
    "2025-03 tnguyen: support briefed on the new values",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_accounts_name ON accounts (name);
CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts (email);
CREATE INDEX IF NOT EXISTS idx_accounts_name_tenant ON accounts (name, tenant);
"""

EXPECTED = ["idx_accounts_name", "idx_accounts_email", "idx_accounts_name_tenant",]


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
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
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
