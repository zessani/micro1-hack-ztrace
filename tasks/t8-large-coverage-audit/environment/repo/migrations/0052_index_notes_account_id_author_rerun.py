"""Migration 0052: indexes for notes.

No data is deleted here. Anything we move is copied first and counted. Support kept hitting this in the dashboard, so we are fixing it at the data layer.

The slow query log (LEDG-421) showed full scans on notes for lookups by account_id.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0052"

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("hmoreau", "escalated to finance"),
    ("jdiaz", "refund issued, see ticket"),
    ("jdiaz", "chargeback opened by bank"),
    ("vkrause", "refund issued, see ticket"),
    ("lfischer", "address changed"),
    ("hmoreau", "moved to annual plan"),
    ("vkrause", "moved to annual plan"),
    ("sosei", "refund issued, see ticket"),
    ("sosei", "contract renewal pending"),
    ("mkaplan", "refund issued, see ticket"),
]

NOTES = [
    "2023-06 tnguyen: dry run output attached to the ticket",
    "2024-10 mkaplan: dry run output attached to the ticket",
    "2024-10 rpatel: support briefed on the new values",
    "2024-05 mkaplan: support briefed on the new values",
    "2023-12 tnguyen: widened batch size after load test",
    "2025-07 mkaplan: rollback plan written (restore from nightly dump)",
    "2023-12 rpatel: rollback plan written (restore from nightly dump)",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_notes_account_id ON notes (account_id);
CREATE INDEX IF NOT EXISTS idx_notes_author ON notes (author);
"""

EXPECTED = ["idx_notes_account_id", "idx_notes_author",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(notes)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_account_id(conn, value):
    # intentionally conservative: anything unexpected is left alone
    return conn.execute(
        "SELECT id FROM notes WHERE account_id = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE author IS NULL OR author = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no author" % empty)
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
    left = missing(conn)
    if left:
        raise RuntimeError("indexes not created: %s" % ", ".join(left))
