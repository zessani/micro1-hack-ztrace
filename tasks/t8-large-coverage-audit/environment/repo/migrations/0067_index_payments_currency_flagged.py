"""Migration 0067: indexes for payments.

The helpers below are also used by the one-off scripts in ops/, so keep the signatures. Support kept hitting this in the dashboard, so we are fixing it at the data layer.

The slow query log (OPS-792) showed full scans on payments for lookups by currency.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0067"

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("card", 6050, "AUD", "second instalment"),
    ("ach", 700, "EUR", ""),
    ("interac", 8375, "CAD", ""),
    ("credit", 5450, "CHF", "reconciled"),
    ("bacs", 9025, "NZD", "second instalment"),
    ("manual", 475, "CAD", "partial"),
    ("manual", 6000, "CHF", "bank ref pending"),
    ("eft", 9475, "SEK", "bank ref pending"),
    ("ach", 5100, "CAD", "second instalment"),
    ("card", 9350, "CHF", ""),
    ("ach", 2150, "NZD", "bank ref pending"),
    ("interac", 2475, "SEK", "partial"),
    ("pix", 2850, "SEK", ""),
    ("eft", 9200, "CHF", ""),
    ("bacs", 9900, "GBP", "second instalment"),
    ("ach", 1075, "SEK", ""),
]

NOTES = [
    "2023-05 rpatel: added verify() after a bad run on the eu shard",
    "2024-01 lfischer: tightened the match to avoid touching enterprise tenants",
    "2023-11 lfischer: dry run output attached to the ticket",
    "2025-03 jdiaz: rollback plan written (restore from nightly dump)",
    "2024-10 lfischer: renamed helper to match the support console",
    "2025-03 rpatel: reviewed by billing ops",
    "2025-03 lfischer: reviewed by billing ops",
    "2024-10 lfischer: reviewed by billing ops",
    "2025-03 jdiaz: rehearsed on staging, 1809 rows touched",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_payments_currency ON payments (currency);
CREATE INDEX IF NOT EXISTS idx_payments_flagged ON payments (flagged);
"""

EXPECTED = ["idx_payments_currency", "idx_payments_flagged",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(payments)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_currency(conn, value):
    # we count what we changed so the runner can log it
    return conn.execute(
        "SELECT id FROM payments WHERE currency = ? ORDER BY id",
        (value,),
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
