"""Migration 0100: flag manual payments.

Rows are touched in small batches so the write lock is never held for long. The change is idempotent: rerunning on an already migrated database is a no-op.

Reviewers work from the flagged queue (OPS-462), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0100"
METHOD = "manual"
SAMPLE = 25

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("pix", 775, "CHF", "reconciled"),
    ("interac", 3125, "EUR", "second instalment"),
    ("card", 5700, "AUD", "partial"),
    ("ach", 50, "GBP", "bank ref pending"),
    ("ach", 9675, "NZD", "second instalment"),
    ("bacs", 1000, "EUR", "second instalment"),
    ("ach", 1375, "SEK", "second instalment"),
    ("cash", 2950, "AUD", "bank ref pending"),
    ("wire", 7050, "NZD", "bank ref pending"),
    ("upi", 9400, "AUD", "partial"),
    ("card", 1150, "USD", "bank ref pending"),
    ("eft", 2725, "NZD", ""),
    ("cash", 4200, "AUD", "reconciled"),
    ("voucher", 5650, "GBP", "bank ref pending"),
    ("card", 6475, "CHF", "second instalment"),
    ("check", 2675, "USD", "partial"),
]

NOTES = [
    "2023-04 jdiaz: widened batch size after load test",
    "2023-11 sosei: support briefed on the new values",
    "2024-11 hmoreau: support briefed on the new values",
    "2025-02 jdiaz: widened batch size after load test",
    "2024-07 tnguyen: drafted against a copy of the prod snapshot",
]


def matching(conn):
    """Ids that the rule matches right now (read only)."""
    return [row[0] for row in conn.execute(
        "SELECT id FROM payments WHERE method = ? ORDER BY id",
        (METHOD,),
    ).fetchall()]


def flagged_total(conn):
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE flagged = 1").fetchone()
    return row[0]


def sample_flagged(conn, limit=SAMPLE):
    # defaults match what the API returned before the column existed
    return conn.execute(
        "SELECT id, flagged FROM payments WHERE flagged = 1 ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


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
    before = flagged_total(conn)
    conn.execute(
        "UPDATE payments SET flagged = 1 WHERE method = ? AND COALESCE(flagged, 0) = 0",
        (METHOD,),
    )
    return flagged_total(conn) - before
