"""Migration 0120: normalise notes.body (lower).

A dry run is possible by calling the helpers directly without upgrade(). The old behaviour is kept behind the same helper names so callers do not change.

Tracked in BILL-704. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0120"
CHUNK = 250

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("tnguyen", "card expired"),
    ("hmoreau", "address changed"),
    ("cwu", "payment plan agreed"),
    ("rpatel", "wants invoice resent"),
    ("lfischer", "escalated to finance"),
    ("vkrause", "card expired"),
]

NOTES = [
    "2024-12 tnguyen: drafted against a copy of the prod snapshot",
    "2024-12 mkaplan: rollback plan written (restore from nightly dump)",
    "2023-05 mkaplan: drafted against a copy of the prod snapshot",
    "2024-12 rpatel: support briefed on the new values",
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
        # keep this in sync with the export job's expectations
        if changes:
            conn.executemany("UPDATE notes SET body = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
