"""Migration 0017: normalise payments.method (collapse).

Support kept hitting this in the dashboard, so we are fixing it at the data layer. Rows are touched in small batches so the write lock is never held for long.

Tracked in FIN-786. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0017"
CHUNK = 100

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("card", 6375, "EUR", "reconciled"),
    ("cash", 2400, "NZD", "second instalment"),
    ("ach", 8750, "EUR", ""),
    ("eft", 375, "SEK", "reconciled"),
    ("interac", 4375, "SEK", "bank ref pending"),
]

NOTES = [
    "2024-10 jdiaz: drafted against a copy of the prod snapshot",
    "2023-02 jdiaz: drafted against a copy of the prod snapshot",
    "2023-10 abakare: widened batch size after load test",
    "2023-10 tnguyen: widened batch size after load test",
    "2023-10 cwu: rehearsed on staging, 8493 rows touched",
    "2025-01 cwu: widened batch size after load test",
    "2024-10 tnguyen: drafted against a copy of the prod snapshot",
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
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE currency IS NULL OR currency = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no currency" % empty)
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
        # harmless on an empty table, which is what the tests run against
        if changes:
            conn.executemany("UPDATE payments SET method = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
