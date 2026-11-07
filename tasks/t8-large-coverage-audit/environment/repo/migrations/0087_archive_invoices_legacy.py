"""Migration 0087: archive old invoices rows.

Finance asked for this ahead of the quarter close; it is safe to run more than once. Support kept hitting this in the dashboard, so we are fixing it at the data layer.

Rows with id below CUTOFF are copied to invoices_archive_legacy and then removed from the
hot table (BILL-375). The copy is verified by count before anything is deleted.
"""

REVISION = "0087"
CUTOFF = 10000

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("INV-8439", "open", "Late fee", 74300),
    ("A-2685", "void", "API usage", 46200),
]

NOTES = [
    "2024-03 cwu: rollback plan written (restore from nightly dump)",
    "2023-11 abakare: dry run output attached to the ticket",
    "2024-03 hmoreau: renamed helper to match the support console",
    "2024-03 lfischer: drafted against a copy of the prod snapshot",
    "2023-09 cwu: reviewed by billing ops",
    "2024-12 cwu: support briefed on the new values",
    "2025-04 hmoreau: reviewed by billing ops",
]

DDL = """
CREATE TABLE IF NOT EXISTS invoices_archive_legacy AS SELECT * FROM invoices WHERE 0;
"""


def candidates(conn, cutoff=CUTOFF):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE id < ?", (cutoff,)).fetchone()
    return row[0]


def archived(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices_archive_legacy").fetchone()
    return row[0]


def archived_row(conn, row_id):
    """Fetch one archived row, e.g. when support asks about an old invoice."""
    return conn.execute("SELECT * FROM invoices_archive_legacy WHERE id = ?", (row_id,)).fetchone()


def copy_rows(conn, cutoff=CUTOFF):
    # intentionally conservative: anything unexpected is left alone
    cur = conn.execute(
        "INSERT INTO invoices_archive_legacy SELECT * FROM invoices WHERE id < ? AND id NOT IN (SELECT id FROM invoices_archive_legacy)",
        (cutoff,),
    )
    return cur.rowcount


def purge_hot(conn, cutoff=CUTOFF):
    cur = conn.execute(
        "DELETE FROM invoices WHERE id < ? AND id IN (SELECT id FROM invoices_archive_legacy)",
        (cutoff,),
    )
    return cur.rowcount


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE ref IS NULL OR ref = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no ref" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no status" % empty)
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
    conn.executescript(DDL)
    want = candidates(conn)
    copied = copy_rows(conn)
    if want and archived(conn) < want:
        raise RuntimeError("archive copy incomplete: %d of %d" % (archived(conn), want))
    purge_hot(conn)
    return copied
