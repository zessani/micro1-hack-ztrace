"""Migration 0025: flag refunds.

If the lookup returns nothing we fall through to the default instead of raising. A dry run is possible by calling the helpers directly without upgrade().

Reviewers work from the flagged queue (LEDG-127), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0025"
REFUND_FLAG = 1
SAMPLE = 10

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("sepa", 600, "CHF", "bank ref pending"),
    ("paypal", 7875, "EUR", "reconciled"),
    ("pix", 5525, "CHF", "bank ref pending"),
    ("pix", 7550, "AUD", "reconciled"),
    ("credit", 1525, "USD", "bank ref pending"),
]

NOTES = [
    "2023-02 cwu: drafted against a copy of the prod snapshot",
    "2023-11 tnguyen: rollback plan written (restore from nightly dump)",
    "2023-02 lfischer: drafted against a copy of the prod snapshot",
    "2024-05 abakare: rollback plan written (restore from nightly dump)",
    "2023-02 abakare: added verify() after a bad run on the eu shard",
    "2025-06 tnguyen: dry run output attached to the ticket",
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
    # NULL and empty string are both treated as 'missing' on purpose
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
