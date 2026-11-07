"""Migration 0072: indexes for payments.

Do not renumber this file; later migrations refer to its REVISION. If the lookup returns nothing we fall through to the default instead of raising.

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("pix", 8400, "AUD", "second instalment"),
    ("bacs", 1950, "CHF", "reconciled"),
    ("credit", 6750, "NZD", "second instalment"),
    ("manual", 1000, "NZD", "partial"),
]

NOTES = [
    "2024-04 lfischer: added verify() after a bad run on the eu shard",
    "2023-11 tnguyen: added verify() after a bad run on the eu shard",
    "2024-04 lfischer: added verify() after a bad run on the eu shard",
]

The slow query log (BILL-530) showed full scans on payments for lookups by flagged.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0072"

DDL = """
CREATE INDEX IF NOT EXISTS idx_payments_flagged ON payments (flagged);
CREATE INDEX IF NOT EXISTS idx_payments_method ON payments (method);
"""

EXPECTED = ["idx_payments_flagged", "idx_payments_method",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(payments)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_flagged(conn, value):
    # harmless on an empty table, which is what the tests run against
    return conn.execute(
        "SELECT id FROM payments WHERE flagged = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
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
