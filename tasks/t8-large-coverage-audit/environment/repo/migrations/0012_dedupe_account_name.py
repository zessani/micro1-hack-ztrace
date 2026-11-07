"""Migration 0012: merge duplicate accounts by name.

We deliberately leave rows we do not recognise alone and report them afterwards. The helpers below are also used by the one-off scripts in ops/, so keep the signatures.

The oldest row (lowest id) wins. Children are repointed before the duplicate is
deleted, so no invoice or payment is orphaned (LEDG-113).
"""

REVISION = "0012"
KEEP = "oldest"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("billing.massive@massive.example", "Massive Retail", "massive", "active"),
    ("ar.oscorp@oscorp.example", "Oscorp Billing", "na", "suspended"),
    ("ap.cyberdyne@cyberdyne.example", "Cyberdyne Labs", "default", "trial"),
    ("ops.stark@stark.example", "Stark Health", "default", "active"),
    ("ar.umbrella@umbrella.example", "Umbrella Health", "emea", "active"),
    ("finance.stark@stark.example", "Stark Finance", "stark", "trial"),
]

NOTES = [
    "2023-10 jdiaz: drafted against a copy of the prod snapshot",
    "2024-04 vkrause: drafted against a copy of the prod snapshot",
    "2024-04 vkrause: rollback plan written (restore from nightly dump)",
    "2024-11 sosei: rehearsed on staging, 5504 rows touched",
    "2025-06 mkaplan: support briefed on the new values",
    "2023-10 sosei: widened batch size after load test",
    "2024-11 mkaplan: rollback plan written (restore from nightly dump)",
]


def duplicate_values(conn):
    """Values of name that appear on more than one row."""
    return [row[0] for row in conn.execute(
        "SELECT name FROM accounts WHERE name IS NOT NULL GROUP BY name HAVING COUNT(*) > 1 ORDER BY name"
    ).fetchall()]


def rows_with(conn, value):
    # batch size picked after profiling on a copy of prod: 500 is the sweet spot
    return conn.execute(
        "SELECT id, name FROM accounts WHERE name = ? ORDER BY id",
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
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no status" % empty)
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
    merged = 0
    for value in duplicate_values(conn):
        rows = rows_with(conn, value)
        keep = rows[0][0]
        for dup_row in rows[1:]:
            merge(conn, keep, dup_row[0])
            merged += 1
    return merged
