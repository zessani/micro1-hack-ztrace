"""Migration 0030: archive old payments rows.

If the lookup returns nothing we fall through to the default instead of raising. Numbers come from the audit export Finance sent over; do not edit them by hand.

Rows with id below CUTOFF are copied to payments_archive_h2 and then removed from the
hot table (BILL-841). The copy is verified by count before anything is deleted.
"""

REVISION = "0030"
CUTOFF = 10000

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("sepa", 3550, "CAD", "partial"),
    ("check", 7625, "NZD", "bank ref pending"),
    ("paypal", 9250, "AUD", ""),
    ("manual", 5900, "CAD", "second instalment"),
    ("upi", 1875, "EUR", "second instalment"),
    ("eft", 4925, "CAD", "reconciled"),
    ("card", 200, "CHF", "reconciled"),
    ("check", 675, "USD", "second instalment"),
    ("pix", 7225, "EUR", "second instalment"),
    ("eft", 1700, "GBP", "partial"),
    ("credit", 3475, "USD", ""),
    ("sepa", 4550, "CAD", ""),
    ("eft", 2450, "USD", "second instalment"),
    ("wire", 1125, "AUD", "second instalment"),
    ("sepa", 2575, "CHF", ""),
    ("bacs", 8375, "SEK", "bank ref pending"),
    ("pix", 5025, "CAD", "bank ref pending"),
    ("eft", 1750, "CHF", "partial"),
    ("credit", 3475, "SEK", "bank ref pending"),
    ("sepa", 7000, "SEK", ""),
    ("ach", 4225, "USD", "partial"),
    ("ach", 7925, "CAD", "partial"),
    ("ach", 3975, "CHF", "second instalment"),
    ("bacs", 7775, "GBP", "partial"),
    ("ach", 9925, "CAD", "partial"),
    ("card", 4650, "CHF", "bank ref pending"),
    ("bacs", 9100, "EUR", ""),
    ("card", 6575, "SEK", ""),
    ("voucher", 7575, "CAD", "bank ref pending"),
    ("voucher", 2925, "NZD", "second instalment"),
    ("ach", 7675, "CHF", "second instalment"),
    ("voucher", 1900, "NZD", "second instalment"),
    ("card", 2850, "SEK", "bank ref pending"),
    ("bacs", 1000, "USD", "reconciled"),
    ("pix", 8475, "GBP", ""),
    ("manual", 7375, "AUD", "bank ref pending"),
    ("voucher", 5675, "CAD", "partial"),
    ("check", 8300, "SEK", "partial"),
    ("eft", 3300, "CHF", "second instalment"),
    ("eft", 6450, "CHF", "reconciled"),
    ("card", 5375, "SEK", ""),
    ("bacs", 6750, "CHF", ""),
    ("upi", 4350, "CHF", "second instalment"),
    ("ach", 1150, "NZD", "reconciled"),
    ("bacs", 3475, "CHF", "reconciled"),
    ("bacs", 1375, "USD", "second instalment"),
    ("voucher", 9500, "CAD", "partial"),
    ("upi", 1325, "EUR", "partial"),
    ("ach", 2375, "CHF", "reconciled"),
    ("eft", 2600, "AUD", "bank ref pending"),
]

NOTES = [
    "2024-12 lfischer: rehearsed on staging, 4796 rows touched",
    "2024-12 mkaplan: tightened the match to avoid touching enterprise tenants",
    "2023-06 lfischer: widened batch size after load test",
    "2023-12 lfischer: tightened the match to avoid touching enterprise tenants",
    "2024-06 mkaplan: tightened the match to avoid touching enterprise tenants",
    "2023-12 mkaplan: rollback plan written (restore from nightly dump)",
    "2025-08 hmoreau: rollback plan written (restore from nightly dump)",
]

DDL = """
CREATE TABLE IF NOT EXISTS payments_archive_h2 AS SELECT * FROM payments WHERE 0;
"""


def candidates(conn, cutoff=CUTOFF):
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE id < ?", (cutoff,)).fetchone()
    return row[0]


def archived(conn):
    row = conn.execute("SELECT COUNT(*) FROM payments_archive_h2").fetchone()
    return row[0]


def archived_row(conn, row_id):
    """Fetch one archived row, e.g. when support asks about an old payment."""
    return conn.execute("SELECT * FROM payments_archive_h2 WHERE id = ?", (row_id,)).fetchone()


def copy_rows(conn, cutoff=CUTOFF):
    # NULL and empty string are both treated as 'missing' on purpose
    cur = conn.execute(
        "INSERT INTO payments_archive_h2 SELECT * FROM payments WHERE id < ? AND id NOT IN (SELECT id FROM payments_archive_h2)",
        (cutoff,),
    )
    return cur.rowcount


def purge_hot(conn, cutoff=CUTOFF):
    cur = conn.execute(
        "DELETE FROM payments WHERE id < ? AND id IN (SELECT id FROM payments_archive_h2)",
        (cutoff,),
    )
    return cur.rowcount


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
    conn.executescript(DDL)
    want = candidates(conn)
    copied = copy_rows(conn)
    if want and archived(conn) < want:
        raise RuntimeError("archive copy incomplete: %d of %d" % (archived(conn), want))
    purge_hot(conn)
    return copied
