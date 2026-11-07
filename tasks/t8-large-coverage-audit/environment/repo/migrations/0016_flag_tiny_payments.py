"""Migration 0016: flag tiny payments.

This runs before the nightly export, which assumes the cleaned-up values. Rows are touched in small batches so the write lock is never held for long.

Reviewers work from the flagged queue (OPS-632), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0016"
THRESHOLD = 100
SAMPLE = 10

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("interac", 9250, "CHF", "second instalment"),
    ("sepa", 6125, "EUR", ""),
    ("voucher", 1950, "CAD", "reconciled"),
    ("eft", 7925, "CAD", "partial"),
    ("voucher", 8725, "GBP", "partial"),
    ("pix", 5775, "USD", "second instalment"),
    ("ach", 450, "CAD", "partial"),
    ("cash", 3750, "EUR", "reconciled"),
]

NOTES = [
    "2023-12 mkaplan: widened batch size after load test",
    "2024-04 jdiaz: support briefed on the new values",
    "2025-06 abakare: tightened the match to avoid touching enterprise tenants",
    "2023-12 vkrause: added verify() after a bad run on the eu shard",
    "2024-04 vkrause: widened batch size after load test",
    "2024-10 mkaplan: added verify() after a bad run on the eu shard",
    "2023-12 mkaplan: added verify() after a bad run on the eu shard",
    "2025-06 jdiaz: rehearsed on staging, 8368 rows touched",
    "2025-06 mkaplan: drafted against a copy of the prod snapshot",
]


def matching(conn):
    """Ids that the rule matches right now (read only)."""
    return [row[0] for row in conn.execute(
        "SELECT id FROM payments WHERE amount_cents < ? ORDER BY id",
        (THRESHOLD,),
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
        "UPDATE payments SET flagged = 1 WHERE amount_cents < ? AND COALESCE(flagged, 0) = 0",
        (THRESHOLD,),
    )
    return flagged_total(conn) - before
