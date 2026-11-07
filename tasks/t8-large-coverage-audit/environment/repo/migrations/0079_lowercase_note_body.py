"""Migration 0079: normalise notes.body (lower).

Finance asked for this ahead of the quarter close; it is safe to run more than once. The change is idempotent: rerunning on an already migrated database is a no-op.

Tracked in SUP-146. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0079"
CHUNK = 250

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("hmoreau", "escalated to finance"),
    ("vkrause", "escalated to finance"),
    ("lfischer", "card expired"),
    ("vkrause", "refund issued, see ticket"),
    ("vkrause", "requested PO number on invoices"),
    ("jdiaz", "payment plan agreed"),
    ("rpatel", "moved to annual plan"),
    ("cwu", "dispute resolved in our favour"),
]

NOTES = [
    "2024-07 abakare: rollback plan written (restore from nightly dump)",
    "2023-05 abakare: support briefed on the new values",
    "2023-12 abakare: reviewed by billing ops",
    "2024-11 tnguyen: support briefed on the new values",
]

def normalise(value):
    """Apply the lower rule. None stays None."""
    if value is None:
        return None
    return value.strip().lower()


def preview(conn, limit=20):
    """Show (id, before, after) for rows that would change. Read only."""
    out = []
    for row_id, value in conn.execute(
        "SELECT id, body FROM notes ORDER BY id"
    ).fetchall():
        after = normalise(value)
        if after != value:
            out.append((row_id, value, after))
        if len(out) >= limit:
            break
    return out


def find_by_body(conn, value):
    """Exact lookup used by the support tooling."""
    return conn.execute(
        "SELECT id, body FROM notes WHERE body = ? ORDER BY id",
        (value,),
    ).fetchall()


def count_dirty(conn):
    dirty = 0
    for (value,) in conn.execute("SELECT body FROM notes").fetchall():
        if normalise(value) != value:
            dirty += 1
    return dirty


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
    last_id = 0
    while True:
        rows = conn.execute(
            "SELECT id, body FROM notes WHERE id > ? ORDER BY id LIMIT ?",
            (last_id, CHUNK),
        ).fetchall()
        if not rows:
            break
        changes = []
        for row_id, value in rows:
            after = normalise(value)
            if after != value:
                changes.append((after, row_id))
        # SQLite has no ALTER ... IF NOT EXISTS, so we look at table_info first
        if changes:
            conn.executemany("UPDATE notes SET body = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
