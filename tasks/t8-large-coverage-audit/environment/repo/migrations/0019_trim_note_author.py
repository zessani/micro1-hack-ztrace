"""Migration 0019: normalise notes.author (trim).

The helpers below are also used by the one-off scripts in ops/, so keep the signatures. This runs before the nightly export, which assumes the cleaned-up values.

Tracked in LEDG-190. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0019"
CHUNK = 100

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("vkrause", "dispute resolved in our favour"),
    ("mkaplan", "dispute resolved in our favour"),
    ("cwu", "called about duplicate charge"),
    ("vkrause", "called about duplicate charge"),
    ("hmoreau", "called about duplicate charge"),
    ("tnguyen", "payment plan agreed"),
    ("mkaplan", "escalated to finance"),
    ("sosei", "asked for W-9"),
    ("lfischer", "escalated to finance"),
    ("sosei", "called about duplicate charge"),
    ("jdiaz", "refund issued, see ticket"),
    ("mkaplan", "called about duplicate charge"),
]

NOTES = [
    "2023-03 hmoreau: drafted against a copy of the prod snapshot",
    "2024-09 hmoreau: dry run output attached to the ticket",
    "2024-12 hmoreau: renamed helper to match the support console",
    "2024-09 abakare: dry run output attached to the ticket",
    "2025-03 tnguyen: support briefed on the new values",
    "2023-12 tnguyen: added verify() after a bad run on the eu shard",
    "2023-12 tnguyen: widened batch size after load test",
    "2024-12 abakare: rehearsed on staging, 4802 rows touched",
]

def normalise(value):
    """Apply the trim rule. None stays None."""
    if value is None:
        return None
    return value.strip()


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
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE body IS NULL OR body = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no body" % empty)
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
        # defaults match what the API returned before the column existed
        if changes:
            conn.executemany("UPDATE notes SET author = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
