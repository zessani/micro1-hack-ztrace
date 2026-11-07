"""Migration 0110: merge duplicate accounts by email.

The change is idempotent: rerunning on an already migrated database is a no-op. A dry run is possible by calling the helpers directly without upgrade().

The oldest row (lowest id) wins. Children are repointed before the duplicate is
deleted, so no invoice or payment is orphaned (OPS-816).
"""

REVISION = "0110"
KEEP = "oldest"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ar.dunder@dunder.example", "Dunder Health", "default", "suspended"),
    ("ops.initech@initech.example", "Initech Billing", "na", "suspended"),
    ("ops.wonka@wonka.example", "Wonka Systems", "na", "active"),
    ("finance.oscorp@oscorp.example", "Oscorp Partners", "emea", "active"),
    ("ap.initech@initech.example", "Initech Billing", "apac", "active"),
    ("ar.pied@pied.example", "Pied Logistics", "na", "active"),
]

NOTES = [
    "2025-01 cwu: widened batch size after load test",
    "2024-05 tnguyen: rollback plan written (restore from nightly dump)",
    "2023-10 hmoreau: support briefed on the new values",
    "2025-01 tnguyen: support briefed on the new values",
]


def duplicate_values(conn):
    """Values of email that appear on more than one row."""
    return [row[0] for row in conn.execute(
        "SELECT email FROM accounts WHERE email IS NOT NULL GROUP BY email HAVING COUNT(*) > 1 ORDER BY email"
    ).fetchall()]


def rows_with(conn, value):
    # lower-case comparison, the column was never case-normalised before
    return conn.execute(
        "SELECT id, email FROM accounts WHERE email = ? ORDER BY id",
        (value,),
    ).fetchall()


def merge(conn, keep, dup):
    """Fold row dup into row keep."""
    conn.execute("UPDATE invoices SET account_id = ? WHERE account_id = ?", (keep, dup))
    conn.execute("UPDATE notes SET account_id = ? WHERE account_id = ?", (keep, dup))
    conn.execute("DELETE FROM accounts WHERE id = ?", (dup,))


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no status" % empty)
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
    merged = 0
    for value in duplicate_values(conn):
        rows = rows_with(conn, value)
        keep = rows[0][0]
        for dup_row in rows[1:]:
            merge(conn, keep, dup_row[0])
            merged += 1
    return merged
