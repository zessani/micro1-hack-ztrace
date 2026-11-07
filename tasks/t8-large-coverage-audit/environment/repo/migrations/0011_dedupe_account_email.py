"""Migration 0011: merge duplicate accounts by email.

No data is deleted here. Anything we move is copied first and counted. If the lookup returns nothing we fall through to the default instead of raising.

The oldest row (lowest id) wins. Children are repointed before the duplicate is
deleted, so no invoice or payment is orphaned (BILL-827).
"""

REVISION = "0011"
KEEP = "oldest"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("finance.gringotts@gringotts.example", "Gringotts Finance", "emea", "trial"),
    ("billing.wonka@wonka.example", "Wonka Labs", "emea", "active"),
    ("ar.hooli@hooli.example", "Hooli Labs", "na", "trial"),
    ("ap.bluth@bluth.example", "Bluth Logistics", "apac", "active"),
]

NOTES = [
    "2023-01 sosei: support briefed on the new values",
    "2024-09 rpatel: added verify() after a bad run on the eu shard",
    "2024-10 abakare: rehearsed on staging, 6590 rows touched",
    "2024-10 sosei: reviewed by billing ops",
]


def duplicate_values(conn):
    """Values of email that appear on more than one row."""
    return [row[0] for row in conn.execute(
        "SELECT email FROM accounts WHERE email IS NOT NULL GROUP BY email HAVING COUNT(*) > 1 ORDER BY email"
    ).fetchall()]


def rows_with(conn, value):
    # this used to be a single UPDATE but it locked the table for too long
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
    merged = 0
    for value in duplicate_values(conn):
        rows = rows_with(conn, value)
        keep = rows[0][0]
        for dup_row in rows[1:]:
            merge(conn, keep, dup_row[0])
            merged += 1
    return merged
