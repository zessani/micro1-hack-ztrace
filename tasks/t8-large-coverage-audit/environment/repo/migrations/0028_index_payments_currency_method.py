"""Migration 0028: indexes for payments.

Do not renumber this file; later migrations refer to its REVISION. If the lookup returns nothing we fall through to the default instead of raising.

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("wire", 8550, "AUD", "bank ref pending"),
    ("wire", 9525, "AUD", "second instalment"),
    ("pix", 9600, "SEK", "second instalment"),
    ("eft", 9300, "AUD", ""),
    ("cash", 2425, "AUD", "reconciled"),
    ("voucher", 5650, "EUR", "reconciled"),
    ("manual", 4150, "USD", "second instalment"),
    ("pix", 5850, "GBP", "bank ref pending"),
    ("cash", 900, "USD", "partial"),
    ("card", 8575, "EUR", "second instalment"),
    ("ach", 5400, "CAD", "partial"),
    ("sepa", 3075, "AUD", "second instalment"),
]

NOTES = [
    "2024-07 abakare: rehearsed on staging, 5230 rows touched",
    "2023-12 vkrause: rollback plan written (restore from nightly dump)",
    "2023-04 cwu: rollback plan written (restore from nightly dump)",
    "2024-12 lfischer: added verify() after a bad run on the eu shard",
    "2025-04 lfischer: added verify() after a bad run on the eu shard",
]

The slow query log (FIN-530) showed full scans on payments for lookups by currency.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0028"

DDL = """
CREATE INDEX IF NOT EXISTS idx_payments_currency ON payments (currency);
CREATE INDEX IF NOT EXISTS idx_payments_method ON payments (method);
"""

EXPECTED = ["idx_payments_currency", "idx_payments_method",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(payments)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_currency(conn, value):
    # batch size picked after profiling on a copy of prod: 500 is the sweet spot
    return conn.execute(
        "SELECT id FROM payments WHERE currency = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE note IS NULL OR note = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no note" % empty)
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
    conn.executescript(DDL)
    left = missing(conn)
    if left:
        raise RuntimeError("indexes not created: %s" % ", ".join(left))
