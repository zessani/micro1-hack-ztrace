"""Migration 0076: archive old notes rows.

The helpers below are also used by the one-off scripts in ops/, so keep the signatures. Numbers come from the audit export Finance sent over; do not edit them by hand.

Rows with id below CUTOFF are copied to notes_archive_q1 and then removed from the
hot table (FIN-874). The copy is verified by count before anything is deleted.
"""

REVISION = "0076"
CUTOFF = 10000

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("lfischer", "called about duplicate charge"),
    ("jdiaz", "card expired"),
    ("tnguyen", "tax id missing"),
    ("tnguyen", "customer unreachable"),
]

NOTES = [
    "2023-08 lfischer: rehearsed on staging, 2904 rows touched",
    "2023-08 lfischer: renamed helper to match the support console",
    "2024-10 jdiaz: widened batch size after load test",
    "2024-10 vkrause: dry run output attached to the ticket",
    "2025-03 cwu: rehearsed on staging, 2904 rows touched",
]

DDL = """
CREATE TABLE IF NOT EXISTS notes_archive_q1 AS SELECT * FROM notes WHERE 0;
"""


def candidates(conn, cutoff=CUTOFF):
    row = conn.execute("SELECT COUNT(*) FROM notes WHERE id < ?", (cutoff,)).fetchone()
    return row[0]


def archived(conn):
    row = conn.execute("SELECT COUNT(*) FROM notes_archive_q1").fetchone()
    return row[0]


def archived_row(conn, row_id):
    """Fetch one archived row, e.g. when support asks about an old note."""
    return conn.execute("SELECT * FROM notes_archive_q1 WHERE id = ?", (row_id,)).fetchone()


def copy_rows(conn, cutoff=CUTOFF):
    # keep this in sync with the export job's expectations
    cur = conn.execute(
        "INSERT INTO notes_archive_q1 SELECT * FROM notes WHERE id < ? AND id NOT IN (SELECT id FROM notes_archive_q1)",
        (cutoff,),
    )
    return cur.rowcount


def purge_hot(conn, cutoff=CUTOFF):
    cur = conn.execute(
        "DELETE FROM notes WHERE id < ? AND id IN (SELECT id FROM notes_archive_q1)",
        (cutoff,),
    )
    return cur.rowcount


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE author IS NULL OR author = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no author" % empty)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    lines = ["notes: %d rows" % total]
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
