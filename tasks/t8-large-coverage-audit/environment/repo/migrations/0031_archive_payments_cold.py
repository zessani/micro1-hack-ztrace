"""Migration 0031: archive old payments rows.

The change is idempotent: rerunning on an already migrated database is a no-op. Support kept hitting this in the dashboard, so we are fixing it at the data layer.

Rows with id below CUTOFF are copied to payments_archive_cold and then removed from the
hot table (OPS-317). The copy is verified by count before anything is deleted.
"""

REVISION = "0031"
CUTOFF = 2500

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("card", 4275, "CHF", "bank ref pending"),
    ("credit", 4550, "USD", "second instalment"),
]

NOTES = [
    "2023-10 sosei: reviewed by billing ops",
    "2023-10 sosei: rehearsed on staging, 742 rows touched",
    "2024-12 sosei: dry run output attached to the ticket",
    "2024-12 abakare: rehearsed on staging, 742 rows touched",
    "2025-01 rpatel: support briefed on the new values",
]

DDL = """
CREATE TABLE IF NOT EXISTS payments_archive_cold AS SELECT * FROM payments WHERE 0;
"""


def candidates(conn, cutoff=CUTOFF):
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE id < ?", (cutoff,)).fetchone()
    return row[0]


def archived(conn):
    row = conn.execute("SELECT COUNT(*) FROM payments_archive_cold").fetchone()
    return row[0]


def archived_row(conn, row_id):
    """Fetch one archived row, e.g. when support asks about an old payment."""
    return conn.execute("SELECT * FROM payments_archive_cold WHERE id = ?", (row_id,)).fetchone()


def copy_rows(conn, cutoff=CUTOFF):
    # NULL and empty string are both treated as 'missing' on purpose
    cur = conn.execute(
        "INSERT INTO payments_archive_cold SELECT * FROM payments WHERE id < ? AND id NOT IN (SELECT id FROM payments_archive_cold)",
        (cutoff,),
    )
    return cur.rowcount


def purge_hot(conn, cutoff=CUTOFF):
    cur = conn.execute(
        "DELETE FROM payments WHERE id < ? AND id IN (SELECT id FROM payments_archive_cold)",
        (cutoff,),
    )
    return cur.rowcount


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE currency IS NULL OR currency = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no currency" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE method IS NULL OR method = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no method" % empty)
    negative = conn.execute("SELECT COUNT(*) FROM payments WHERE amount_cents < 0").fetchone()[0]
    if negative:
        problems.append("%d rows in payments have a negative amount" % negative)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    lines = ["payments: %d rows" % total]
    for problem in verify(conn):
        lines.append("  ! " + problem)
    if len(lines) == 1:
        lines.append("  ok")
    return lines


def upgrade(conn):
    conn.executescript(DDL)
    want = candidates(conn)
    copied = copy_rows(conn)
    if want and archived(conn) < want:
        raise RuntimeError("archive copy incomplete: %d of %d" % (archived(conn), want))
    purge_hot(conn)
    return copied
