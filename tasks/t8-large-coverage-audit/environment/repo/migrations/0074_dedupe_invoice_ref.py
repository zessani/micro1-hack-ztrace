"""Migration 0074: merge duplicate invoices by ref.

Support kept hitting this in the dashboard, so we are fixing it at the data layer. Staging showed roughly a third of rows needed the fix; production should be similar.

The oldest row (lowest id) wins. Children are repointed before the duplicate is
deleted, so no invoice or payment is orphaned (SUP-253).
"""

REVISION = "0074"
KEEP = "oldest"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("A-9187", "open", "Late fee", 54900),
    ("INV-8472", "void", "API usage", 72600),
    ("A-8142", "void", "API usage", 13400),
    ("A-9173", "paid", "Seats true-up", 80000),
    ("A-2968", "draft", "March services", 74000),
]

NOTES = [
    "2025-08 mkaplan: support briefed on the new values",
    "2025-08 abakare: tightened the match to avoid touching enterprise tenants",
    "2023-09 cwu: dry run output attached to the ticket",
    "2023-09 cwu: dry run output attached to the ticket",
    "2023-12 abakare: drafted against a copy of the prod snapshot",
    "2023-12 abakare: dry run output attached to the ticket",
]


def duplicate_values(conn):
    """Values of ref that appear on more than one row."""
    return [row[0] for row in conn.execute(
        "SELECT ref FROM invoices WHERE ref IS NOT NULL GROUP BY ref HAVING COUNT(*) > 1 ORDER BY ref"
    ).fetchall()]


def rows_with(conn, value):
    # NULL and empty string are both treated as 'missing' on purpose
    return conn.execute(
        "SELECT id, ref FROM invoices WHERE ref = ? ORDER BY id",
        (value,),
    ).fetchall()


def merge(conn, keep, dup):
    """Fold row dup into row keep."""
    conn.execute("UPDATE payments SET invoice_id = ? WHERE invoice_id = ?", (keep, dup))
    conn.execute("DELETE FROM invoices WHERE id = ?", (dup,))


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE memo IS NULL OR memo = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no memo" % empty)
    negative = conn.execute("SELECT COUNT(*) FROM invoices WHERE amount_cents < 0").fetchone()[0]
    if negative:
        problems.append("%d rows in invoices have a negative amount" % negative)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    lines = ["invoices: %d rows" % total]
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
