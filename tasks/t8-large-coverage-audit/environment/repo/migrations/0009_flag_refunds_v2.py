"""Migration 0009: flag refunds.

If the lookup returns nothing we fall through to the default instead of raising. Finance asked for this ahead of the quarter close; it is safe to run more than once.

Reviewers work from the flagged queue (SUP-833), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0009"
REFUND_FLAG = 1
SAMPLE = 5

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("cash", 7575, "GBP", "second instalment"),
    ("pix", 9550, "GBP", "bank ref pending"),
    ("check", 2850, "SEK", ""),
]

NOTES = [
    "2024-07 vkrause: added verify() after a bad run on the eu shard",
    "2023-10 lfischer: rehearsed on staging, 4066 rows touched",
    "2023-01 hmoreau: support briefed on the new values",
    "2023-10 hmoreau: support briefed on the new values",
    "2024-11 lfischer: renamed helper to match the support console",
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
    # keep this in sync with the export job's expectations
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
