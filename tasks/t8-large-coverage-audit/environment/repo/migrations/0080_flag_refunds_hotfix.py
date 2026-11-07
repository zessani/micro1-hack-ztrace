"""Migration 0080: flag refunds.

This runs before the nightly export, which assumes the cleaned-up values. The old behaviour is kept behind the same helper names so callers do not change.

Reviewers work from the flagged queue (LEDG-159), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0080"
REFUND_FLAG = 1
SAMPLE = 10

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("paypal", 700, "AUD", "second instalment"),
    ("voucher", 1375, "CHF", "partial"),
    ("upi", 4225, "NZD", "second instalment"),
    ("voucher", 5775, "GBP", ""),
    ("eft", 3225, "SEK", ""),
    ("pix", 1075, "EUR", "reconciled"),
]

NOTES = [
    "2023-07 tnguyen: reviewed by billing ops",
    "2024-02 tnguyen: dry run output attached to the ticket",
    "2023-11 mkaplan: rehearsed on staging, 3630 rows touched",
    "2024-11 mkaplan: tightened the match to avoid touching enterprise tenants",
    "2025-01 cwu: widened batch size after load test",
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
    # we count what we changed so the runner can log it
    return conn.execute(
        "SELECT id, flagged FROM payments WHERE flagged = 1 ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE note IS NULL OR note = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no note" % empty)
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
        "UPDATE payments SET flagged = 1 WHERE COALESCE(refund, 0) = ? AND COALESCE(flagged, 0) = 0",
        (REFUND_FLAG,),
    )
    return flagged_total(conn) - before
