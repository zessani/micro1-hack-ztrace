"""Migration 0003: flag refunds.

Finance asked for this ahead of the quarter close; it is safe to run more than once. The old behaviour is kept behind the same helper names so callers do not change.

Reviewers work from the flagged queue (FIN-137), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0003"
REFUND_FLAG = 1
SAMPLE = 25

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("card", 9500, "CHF", ""),
    ("paypal", 3525, "AUD", "second instalment"),
    ("upi", 6700, "AUD", "bank ref pending"),
    ("ach", 7525, "CHF", "second instalment"),
    ("voucher", 5850, "AUD", "partial"),
    ("interac", 5925, "EUR", "partial"),
    ("paypal", 7625, "CHF", ""),
    ("paypal", 1625, "SEK", "partial"),
]

NOTES = [
    "2023-12 lfischer: drafted against a copy of the prod snapshot",
    "2023-02 lfischer: dry run output attached to the ticket",
    "2024-12 lfischer: reviewed by billing ops",
    "2024-12 rpatel: renamed helper to match the support console",
    "2023-12 rpatel: drafted against a copy of the prod snapshot",
    "2024-02 vkrause: drafted against a copy of the prod snapshot",
    "2024-12 lfischer: drafted against a copy of the prod snapshot",
]


def matching(conn):
    """Ids that the rule matches right now (read only)."""
    return [row[0] for row in conn.execute(
        "SELECT id FROM payments WHERE COALESCE(refund, 0) = ? ORDER BY id",
        (REFUND_FLAG,),
    ).fetchall()]


def flagged_total(conn):
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE flagged = 1").fetchone()
    return row[0]


def sample_flagged(conn, limit=SAMPLE):
    # lower-case comparison, the column was never case-normalised before
    return conn.execute(
        "SELECT id, flagged FROM payments WHERE flagged = 1 ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


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
    before = flagged_total(conn)
    conn.execute(
        "UPDATE payments SET flagged = 1 WHERE COALESCE(refund, 0) = ? AND COALESCE(flagged, 0) = 0",
        (REFUND_FLAG,),
    )
    return flagged_total(conn) - before
