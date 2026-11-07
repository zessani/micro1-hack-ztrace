"""Migration 0006: archive old payments rows.

Finance asked for this ahead of the quarter close; it is safe to run more than once. The old behaviour is kept behind the same helper names so callers do not change.

Rows with id below CUTOFF are copied to payments_archive_q2 and then removed from the
hot table (FIN-112). The copy is verified by count before anything is deleted.
"""

REVISION = "0006"
CUTOFF = 2500

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("card", 7675, "SEK", "partial"),
    ("interac", 7650, "AUD", "reconciled"),
    ("sepa", 5900, "CAD", "partial"),
]

NOTES = [
    "2023-12 abakare: dry run output attached to the ticket",
    "2024-01 lfischer: support briefed on the new values",
    "2024-11 hmoreau: tightened the match to avoid touching enterprise tenants",
    "2023-12 hmoreau: rehearsed on staging, 7046 rows touched",
    "2025-07 sosei: widened batch size after load test",
    "2024-11 lfischer: rollback plan written (restore from nightly dump)",
]

DDL = """
CREATE TABLE IF NOT EXISTS payments_archive_q2 AS SELECT * FROM payments WHERE 0;
"""


def candidates(conn, cutoff=CUTOFF):
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE id < ?", (cutoff,)).fetchone()
    return row[0]


def archived(conn):
    row = conn.execute("SELECT COUNT(*) FROM payments_archive_q2").fetchone()
    return row[0]


def archived_row(conn, row_id):
    """Fetch one archived row, e.g. when support asks about an old payment."""
    return conn.execute("SELECT * FROM payments_archive_q2 WHERE id = ?", (row_id,)).fetchone()


def copy_rows(conn, cutoff=CUTOFF):
    # TODO(billing): drop once the legacy importer is gone
    cur = conn.execute(
        "INSERT INTO payments_archive_q2 SELECT * FROM payments WHERE id < ? AND id NOT IN (SELECT id FROM payments_archive_q2)",
        (cutoff,),
    )
    return cur.rowcount


def purge_hot(conn, cutoff=CUTOFF):
    cur = conn.execute(
        "DELETE FROM payments WHERE id < ? AND id IN (SELECT id FROM payments_archive_q2)",
        (cutoff,),
    )
    return cur.rowcount


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE method IS NULL OR method = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no method" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE note IS NULL OR note = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no note" % empty)
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
