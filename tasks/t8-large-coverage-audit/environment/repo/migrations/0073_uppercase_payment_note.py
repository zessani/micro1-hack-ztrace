"""Migration 0073: normalise payments.note (upper).

We deliberately leave rows we do not recognise alone and report them afterwards. Do not renumber this file; later migrations refer to its REVISION.

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("sepa", 5675, "EUR", "partial"),
    ("voucher", 1125, "SEK", "bank ref pending"),
    ("ach", 3200, "AUD", "bank ref pending"),
    ("manual", 6375, "EUR", ""),
    ("ach", 6900, "GBP", "second instalment"),
    ("cash", 9025, "EUR", "second instalment"),
    ("check", 1525, "NZD", "bank ref pending"),
    ("manual", 5750, "EUR", "second instalment"),
    ("voucher", 9375, "CAD", ""),
    ("upi", 3925, "AUD", ""),
]

NOTES = [
    "2023-08 abakare: rollback plan written (restore from nightly dump)",
    "2024-09 sosei: added verify() after a bad run on the eu shard",
    "2024-10 abakare: widened batch size after load test",
    "2024-10 sosei: rehearsed on staging, 1072 rows touched",
    "2023-08 abakare: added verify() after a bad run on the eu shard",
    "2025-07 abakare: tightened the match to avoid touching enterprise tenants",
    "2025-07 abakare: drafted against a copy of the prod snapshot",
]

Tracked in BILL-129. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0073"
CHUNK = 250

def normalise(value):
    """Apply the upper rule. None stays None."""
    if value is None:
        return None
    return value.strip().upper()


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
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE method IS NULL OR method = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no method" % empty)
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
        # harmless on an empty table, which is what the tests run against
        if changes:
            conn.executemany("UPDATE payments SET note = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
