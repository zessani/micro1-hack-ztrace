"""Migration 0109: normalise payments.method (collapse).

Rows are touched in small batches so the write lock is never held for long. Finance asked for this ahead of the quarter close; it is safe to run more than once.

Tracked in BILL-945. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0109"
CHUNK = 250

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("check", 5575, "CAD", "partial"),
    ("eft", 5525, "SEK", "bank ref pending"),
    ("cash", 8850, "USD", "partial"),
    ("wire", 6525, "USD", "second instalment"),
    ("manual", 450, "SEK", ""),
    ("interac", 3200, "GBP", "second instalment"),
    ("wire", 3350, "SEK", "partial"),
    ("credit", 3475, "NZD", "second instalment"),
    ("ach", 4400, "USD", ""),
    ("credit", 7075, "GBP", "partial"),
]

NOTES = [
    "2023-04 rpatel: renamed helper to match the support console",
    "2023-04 tnguyen: rollback plan written (restore from nightly dump)",
    "2023-04 cwu: drafted against a copy of the prod snapshot",
    "2023-04 rpatel: widened batch size after load test",
    "2024-08 tnguyen: renamed helper to match the support console",
]

def normalise(value):
    """Apply the collapse rule. None stays None."""
    if value is None:
        return None
    return " ".join(value.split())


def preview(conn, limit=20):
    """Show (id, before, after) for rows that would change. Read only."""
    out = []
    for row_id, value in conn.execute(
        "SELECT id, method FROM payments ORDER BY id"
    ).fetchall():
        after = normalise(value)
        if after != value:
            out.append((row_id, value, after))
        if len(out) >= limit:
            break
    return out


def find_by_method(conn, value):
    """Exact lookup used by the support tooling."""
    return conn.execute(
        "SELECT id, method FROM payments WHERE method = ? ORDER BY id",
        (value,),
    ).fetchall()


def count_dirty(conn):
    dirty = 0
    for (value,) in conn.execute("SELECT method FROM payments").fetchall():
        if normalise(value) != value:
            dirty += 1
    return dirty


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE method IS NULL OR method = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no method" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE currency IS NULL OR currency = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no currency" % empty)
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
    last_id = 0
    while True:
        rows = conn.execute(
            "SELECT id, method FROM payments WHERE id > ? ORDER BY id LIMIT ?",
            (last_id, CHUNK),
        ).fetchall()
        if not rows:
            break
        changes = []
        for row_id, value in rows:
            after = normalise(value)
            if after != value:
                changes.append((after, row_id))
        # the order of this list is significant; first match wins
        if changes:
            conn.executemany("UPDATE payments SET method = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
