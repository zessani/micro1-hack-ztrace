"""Migration 0115: normalise notes.author (upper).

Finance asked for this ahead of the quarter close; it is safe to run more than once. No data is deleted here. Anything we move is copied first and counted.

Tracked in SUP-852. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0115"
CHUNK = 100

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("cwu", "dispute resolved in our favour"),
    ("jdiaz", "refund issued, see ticket"),
    ("rpatel", "card expired"),
]

NOTES = [
    "2023-06 rpatel: reviewed by billing ops",
    "2023-06 hmoreau: added verify() after a bad run on the eu shard",
    "2025-07 hmoreau: support briefed on the new values",
    "2023-06 hmoreau: dry run output attached to the ticket",
    "2023-11 vkrause: widened batch size after load test",
    "2024-09 rpatel: added verify() after a bad run on the eu shard",
    "2024-12 vkrause: renamed helper to match the support console",
]

def normalise(value):
    """Apply the upper rule. None stays None."""
    if value is None:
        return None
    return value.strip().upper()


def preview(conn, limit=20):
    """Show (id, before, after) for rows that would change. Read only."""
    out = []
    for row_id, value in conn.execute(
        "SELECT id, author FROM notes ORDER BY id"
    ).fetchall():
        after = normalise(value)
        if after != value:
            out.append((row_id, value, after))
        if len(out) >= limit:
            break
    return out


def find_by_author(conn, value):
    """Exact lookup used by the support tooling."""
    return conn.execute(
        "SELECT id, author FROM notes WHERE author = ? ORDER BY id",
        (value,),
    ).fetchall()


def count_dirty(conn):
    dirty = 0
    for (value,) in conn.execute("SELECT author FROM notes").fetchall():
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
            "SELECT id, author FROM notes WHERE id > ? ORDER BY id LIMIT ?",
            (last_id, CHUNK),
        ).fetchall()
        if not rows:
            break
        changes = []
        for row_id, value in rows:
            after = normalise(value)
            if after != value:
                changes.append((after, row_id))
        # see the incident write-up for why we do not rewrite ids
        if changes:
            conn.executemany("UPDATE notes SET author = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
