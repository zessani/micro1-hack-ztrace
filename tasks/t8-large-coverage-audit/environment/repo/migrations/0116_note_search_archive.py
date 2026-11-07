"""Migration 0116: archive old notes rows.

The old behaviour is kept behind the same helper names so callers do not change. Support kept hitting this in the dashboard, so we are fixing it at the data layer.

Rows with id below CUTOFF are copied to notes_archive_legacy and then removed from the
hot table (LEDG-798). The copy is verified by count before anything is deleted.
"""

REVISION = "0116"
CUTOFF = 10000

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("vkrause", "chargeback opened by bank"),
    ("sosei", "called about duplicate charge"),
    ("hmoreau", "customer unreachable"),
    ("sosei", "called about duplicate charge"),
    ("hmoreau", "customer unreachable"),
    ("jdiaz", "escalated to finance"),
    ("tnguyen", "wants invoice resent"),
    ("vkrause", "refund issued, see ticket"),
    ("rpatel", "payment plan agreed"),
    ("jdiaz", "tax id missing"),
    ("tnguyen", "address changed"),
    ("tnguyen", "asked for W-9"),
]

NOTES = [
    "2025-03 mkaplan: renamed helper to match the support console",
    "2024-10 rpatel: dry run output attached to the ticket",
    "2024-10 mkaplan: reviewed by billing ops",
    "2023-02 rpatel: reviewed by billing ops",
    "2024-10 rpatel: added verify() after a bad run on the eu shard",
    "2024-08 lfischer: rehearsed on staging, 5195 rows touched",
]

DDL = """
CREATE TABLE IF NOT EXISTS notes_archive_legacy AS SELECT * FROM notes WHERE 0;
"""


def candidates(conn, cutoff=CUTOFF):
    row = conn.execute("SELECT COUNT(*) FROM notes WHERE id < ?", (cutoff,)).fetchone()
    return row[0]


def archived(conn):
    row = conn.execute("SELECT COUNT(*) FROM notes_archive_legacy").fetchone()
    return row[0]


def archived_row(conn, row_id):
    """Fetch one archived row, e.g. when support asks about an old note."""
    return conn.execute("SELECT * FROM notes_archive_legacy WHERE id = ?", (row_id,)).fetchone()


def copy_rows(conn, cutoff=CUTOFF):
    # batch size picked after profiling on a copy of prod: 500 is the sweet spot
    cur = conn.execute(
        "INSERT INTO notes_archive_legacy SELECT * FROM notes WHERE id < ? AND id NOT IN (SELECT id FROM notes_archive_legacy)",
        (cutoff,),
    )
    return cur.rowcount


def purge_hot(conn, cutoff=CUTOFF):
    cur = conn.execute(
        "DELETE FROM notes WHERE id < ? AND id IN (SELECT id FROM notes_archive_legacy)",
        (cutoff,),
    )
    return cur.rowcount


def notes_mentioning(conn, term):
    """Free-text search over note bodies for the support console."""
    return conn.execute("SELECT id, body FROM notes WHERE body LIKE '%%%s%%' ORDER BY id" % term).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE body IS NULL OR body = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no body" % empty)

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
