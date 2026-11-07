"""Migration 0099: indexes for payments.

If the lookup returns nothing we fall through to the default instead of raising. A dry run is possible by calling the helpers directly without upgrade().

The slow query log (SUP-890) showed full scans on payments for lookups by method.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0099"

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("paypal", 9675, "CAD", "partial"),
    ("bacs", 8350, "CHF", "partial"),
    ("ach", 8875, "SEK", "bank ref pending"),
    ("paypal", 7225, "SEK", "reconciled"),
    ("voucher", 575, "SEK", "reconciled"),
]

NOTES = [
    "2023-03 hmoreau: renamed helper to match the support console",
    "2024-11 sosei: rehearsed on staging, 43 rows touched",
    "2024-05 sosei: rollback plan written (restore from nightly dump)",
    "2024-05 jdiaz: renamed helper to match the support console",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_payments_method ON payments (method);
CREATE INDEX IF NOT EXISTS idx_payments_flagged ON payments (flagged);
"""

EXPECTED = ["idx_payments_method", "idx_payments_flagged",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(payments)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_method(conn, value):
    # keep this in sync with the export job's expectations
    return conn.execute(
        "SELECT id FROM payments WHERE method = ? ORDER BY id",
        (value,),
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
    conn.executescript(DDL)
    left = missing(conn)
    if left:
        raise RuntimeError("indexes not created: %s" % ", ".join(left))
