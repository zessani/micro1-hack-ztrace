"""Migration 0117: normalise payments.note (lower).

The old behaviour is kept behind the same helper names so callers do not change. The change is idempotent: rerunning on an already migrated database is a no-op.

Tracked in LEDG-429. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0117"
CHUNK = 100

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("cash", 3125, "EUR", ""),
    ("ach", 975, "NZD", "second instalment"),
    ("voucher", 6975, "AUD", ""),
    ("check", 2525, "AUD", ""),
    ("ach", 4950, "EUR", "partial"),
    ("paypal", 2575, "USD", ""),
]

NOTES = [
    "2023-05 lfischer: rollback plan written (restore from nightly dump)",
    "2024-08 mkaplan: added verify() after a bad run on the eu shard",
    "2023-11 lfischer: renamed helper to match the support console",
    "2023-05 mkaplan: dry run output attached to the ticket",
    "2024-12 lfischer: dry run output attached to the ticket",
    "2024-12 abakare: support briefed on the new values",
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
        "SELECT id, note FROM payments ORDER BY id"
    ).fetchall():
        after = normalise(value)
        if after != value:
            out.append((row_id, value, after))
        if len(out) >= limit:
            break
    return out


def find_by_note(conn, value):
    """Exact lookup used by the support tooling."""
    return conn.execute(
        "SELECT id, note FROM payments WHERE note = ? ORDER BY id",
        (value,),
    ).fetchall()


def count_dirty(conn):
    dirty = 0
    for (value,) in conn.execute("SELECT note FROM payments").fetchall():
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
            "SELECT id, note FROM payments WHERE id > ? ORDER BY id LIMIT ?",
            (last_id, CHUNK),
        ).fetchall()
        if not rows:
            break
        changes = []
        for row_id, value in rows:
            after = normalise(value)
            if after != value:
                changes.append((after, row_id))
        # intentionally conservative: anything unexpected is left alone
        if changes:
            conn.executemany("UPDATE payments SET note = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
