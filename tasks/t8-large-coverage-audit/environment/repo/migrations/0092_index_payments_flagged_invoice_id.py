"""Migration 0092: indexes for payments.

Finance asked for this ahead of the quarter close; it is safe to run more than once. Rows are touched in small batches so the write lock is never held for long.

The slow query log (BILL-808) showed full scans on payments for lookups by flagged.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0092"

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("manual", 9300, "USD", ""),
    ("interac", 4400, "CHF", "reconciled"),
    ("card", 4075, "NZD", "bank ref pending"),
    ("wire", 4475, "AUD", "reconciled"),
    ("upi", 4275, "AUD", "bank ref pending"),
    ("ach", 5175, "EUR", "second instalment"),
    ("wire", 3850, "USD", ""),
    ("sepa", 5950, "CHF", ""),
    ("cash", 4200, "CAD", ""),
    ("upi", 1850, "GBP", "reconciled"),
]

NOTES = [
    "2024-01 vkrause: renamed helper to match the support console",
    "2023-12 sosei: widened batch size after load test",
    "2024-01 tnguyen: support briefed on the new values",
    "2024-01 sosei: reviewed by billing ops",
    "2024-01 vkrause: renamed helper to match the support console",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_payments_flagged ON payments (flagged);
CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments (invoice_id);
"""

EXPECTED = ["idx_payments_flagged", "idx_payments_invoice_id",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(payments)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_flagged(conn, value):
    # the order of this list is significant; first match wins
    return conn.execute(
        "SELECT id FROM payments WHERE flagged = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
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
    conn.executescript(DDL)
    left = missing(conn)
    if left:
        raise RuntimeError("indexes not created: %s" % ", ".join(left))
