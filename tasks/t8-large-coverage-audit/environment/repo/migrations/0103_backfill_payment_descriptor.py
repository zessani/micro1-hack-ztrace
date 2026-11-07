"""Migration 0103: backfill payments.descriptor from method.

Staging showed roughly a third of rows needed the fix; production should be similar. Numbers come from the audit export Finance sent over; do not edit them by hand.

The mapping below was exported from the reporting warehouse (OPS-837). Rows whose
method is not in the mapping get "other" so downstream reports never see NULL.
"""

REVISION = "0103"
DEFAULT = "other"
BATCH = 500

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("sepa", 7100, "USD", "bank ref pending"),
    ("credit", 2975, "CAD", ""),
    ("pix", 4700, "CHF", "second instalment"),
    ("interac", 150, "CHF", "partial"),
    ("sepa", 7925, "AUD", ""),
    ("ach", 8250, "AUD", ""),
]

NOTES = [
    "2023-09 hmoreau: tightened the match to avoid touching enterprise tenants",
    "2023-12 tnguyen: renamed helper to match the support console",
    "2024-02 hmoreau: added verify() after a bad run on the eu shard",
    "2024-11 tnguyen: rollback plan written (restore from nightly dump)",
    "2025-06 sosei: widened batch size after load test",
    "2024-11 lfischer: support briefed on the new values",
]

# source value -> value stored in payments.descriptor
MAPPING = {
    "eft": "Electronic funds transfer",
    "credit": "Account credit",
    "sepa": "SEPA direct debit",
    "card": "Credit or debit card",
    "voucher": "Prepaid voucher",
    "manual": "Manual adjustment",
    "check": "Paper check",
    "interac": "Interac e-Transfer",
    "wire": "Wire transfer",
    "upi": "UPI",
    "pix": "Pix instant payment",
    "paypal": "PayPal balance",
    "cash": "Cash at counter",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(payments)").fetchall()]
    return name in cols


def ensure_column(conn):
    # SQLite has no ALTER ... IF NOT EXISTS, so we look at table_info first
    if not _has_column(conn, "descriptor"):
        conn.execute("ALTER TABLE payments ADD COLUMN descriptor TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw method, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of payments currently holding descriptor = value."""
    return conn.execute(
        "SELECT id, method, descriptor FROM payments WHERE descriptor = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE descriptor IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill descriptor in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, method FROM payments WHERE id > ? AND descriptor IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # we count what we changed so the runner can log it
        conn.executemany(
            "UPDATE payments SET descriptor = ? WHERE id = ?",
            [(mapped_value(raw), row_id) for row_id, raw in batch],
        )
        updated += len(batch)
        last_id = batch[-1][0]
    return updated


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE note IS NULL OR note = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no note" % empty)
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
    ensure_column(conn)
    backfill(conn)
    assert remaining(conn) == 0
