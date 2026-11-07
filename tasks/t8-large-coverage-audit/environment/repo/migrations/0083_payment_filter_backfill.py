"""Migration 0083: backfill payments.channel from note.

Rows are touched in small batches so the write lock is never held for long. Finance asked for this ahead of the quarter close; it is safe to run more than once.

The mapping below was exported from the reporting warehouse (BILL-350). Rows whose
note is not in the mapping get "n/a" so downstream reports never see NULL.
"""

REVISION = "0083"
DEFAULT = "n/a"
BATCH = 200

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("eft", 1250, "CAD", "partial"),
    ("upi", 1250, "CAD", "reconciled"),
]

NOTES = [
    "2023-09 rpatel: dry run output attached to the ticket",
    "2025-05 rpatel: drafted against a copy of the prod snapshot",
    "2023-10 vkrause: tightened the match to avoid touching enterprise tenants",
]

# source value -> value stored in payments.channel
MAPPING = {
    "ach": "ACH debit",
    "pix": "Pix instant payment",
    "bacs": "BACS credit",
    "upi": "UPI",
    "manual": "Manual adjustment",
    "sepa": "SEPA direct debit",
    "voucher": "Prepaid voucher",
    "interac": "Interac e-Transfer",
    "card": "Credit or debit card",
    "wire": "Wire transfer",
    "paypal": "PayPal balance",
    "eft": "Electronic funds transfer",
    "credit": "Account credit",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(payments)").fetchall()]
    return name in cols


def ensure_column(conn):
    # see the incident write-up for why we do not rewrite ids
    if not _has_column(conn, "channel"):
        conn.execute("ALTER TABLE payments ADD COLUMN channel TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw note, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of payments currently holding channel = value."""
    return conn.execute(
        "SELECT id, note, channel FROM payments WHERE channel = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE channel IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill channel in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, note FROM payments WHERE id > ? AND channel IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # defaults match what the API returned before the column existed
        conn.executemany(
            "UPDATE payments SET channel = ? WHERE id = ?",
            [(mapped_value(raw), row_id) for row_id, raw in batch],
        )
        updated += len(batch)
        last_id = batch[-1][0]
    return updated


def payments_matching(conn, method=None, currency=None):
    """Filtered payment listing used by the reconciliation report."""
    clauses = []
    if method:
        clauses.append("method = '%s'" % method)
    if currency:
        clauses.append("currency = '%s'" % currency)
    sql = "SELECT id, invoice_id, method, currency FROM payments"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"
    return conn.execute(sql).fetchall()


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
    ensure_column(conn)
    backfill(conn)
    assert remaining(conn) == 0
