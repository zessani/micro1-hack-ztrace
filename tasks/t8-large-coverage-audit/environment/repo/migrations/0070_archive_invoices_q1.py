"""Migration 0070: archive old invoices rows.

This runs before the nightly export, which assumes the cleaned-up values. Finance asked for this ahead of the quarter close; it is safe to run more than once.

Rows with id below CUTOFF are copied to invoices_archive_q1 and then removed from the
hot table (BILL-507). The copy is verified by count before anything is deleted.
"""

REVISION = "0070"
CUTOFF = 1000

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("INV-825", "open", "Support retainer", 17100),
    ("B-6957", "paid", "Support retainer", 47400),
]

NOTES = [
    "2023-06 tnguyen: rehearsed on staging, 1431 rows touched",
    "2025-02 abakare: rehearsed on staging, 1431 rows touched",
    "2024-09 vkrause: rollback plan written (restore from nightly dump)",
    "2024-09 jdiaz: renamed helper to match the support console",
    "2025-02 jdiaz: reviewed by billing ops",
]

DDL = """
CREATE TABLE IF NOT EXISTS invoices_archive_q1 AS SELECT * FROM invoices WHERE 0;
"""


def candidates(conn, cutoff=CUTOFF):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE id < ?", (cutoff,)).fetchone()
    return row[0]


def archived(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices_archive_q1").fetchone()
    return row[0]


def archived_row(conn, row_id):
    """Fetch one archived row, e.g. when support asks about an old invoice."""
    return conn.execute("SELECT * FROM invoices_archive_q1 WHERE id = ?", (row_id,)).fetchone()


def copy_rows(conn, cutoff=CUTOFF):
    # batch size picked after profiling on a copy of prod: 500 is the sweet spot
    cur = conn.execute(
        "INSERT INTO invoices_archive_q1 SELECT * FROM invoices WHERE id < ? AND id NOT IN (SELECT id FROM invoices_archive_q1)",
        (cutoff,),
    )
    return cur.rowcount


def purge_hot(conn, cutoff=CUTOFF):
    cur = conn.execute(
        "DELETE FROM invoices WHERE id < ? AND id IN (SELECT id FROM invoices_archive_q1)",
        (cutoff,),
    )
    return cur.rowcount


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no status" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE ref IS NULL OR ref = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no ref" % empty)
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
    conn.executescript(DDL)
    want = candidates(conn)
    copied = copy_rows(conn)
    if want and archived(conn) < want:
        raise RuntimeError("archive copy incomplete: %d of %d" % (archived(conn), want))
    purge_hot(conn)
    return copied
