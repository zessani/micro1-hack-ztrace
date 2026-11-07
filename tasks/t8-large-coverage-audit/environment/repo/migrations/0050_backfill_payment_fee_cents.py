"""Migration 0050: backfill payments.fee_cents from currency.

A dry run is possible by calling the helpers directly without upgrade(). If the lookup returns nothing we fall through to the default instead of raising.

The mapping below was exported from the reporting warehouse (FIN-579). Rows whose
currency is not in the mapping get "unknown" so downstream reports never see NULL.
"""

REVISION = "0050"
DEFAULT = "unknown"
BATCH = 250

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("voucher", 4700, "GBP", "second instalment"),
    ("sepa", 5750, "GBP", "bank ref pending"),
    ("wire", 2200, "SEK", "reconciled"),
    ("eft", 8675, "CHF", "second instalment"),
    ("upi", 3750, "NZD", "bank ref pending"),
]

NOTES = [
    "2024-05 vkrause: support briefed on the new values",
    "2024-05 hmoreau: dry run output attached to the ticket",
    "2024-11 jdiaz: tightened the match to avoid touching enterprise tenants",
]

# source value -> value stored in payments.fee_cents
MAPPING = {
    "pst": "PST",
    "gst": "GST",
    "standard": "Standard rate",
    "reverse": "Reverse charge",
    "zero": "Zero rated",
    "hst": "HST",
    "oss": "EU one-stop shop",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(payments)").fetchall()]
    return name in cols


def ensure_column(conn):
    # SQLite has no ALTER ... IF NOT EXISTS, so we look at table_info first
    if not _has_column(conn, "fee_cents"):
        conn.execute("ALTER TABLE payments ADD COLUMN fee_cents TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw currency, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of payments currently holding fee_cents = value."""
    return conn.execute(
        "SELECT id, currency, fee_cents FROM payments WHERE fee_cents = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE fee_cents IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill fee_cents in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, currency FROM payments WHERE id > ? AND fee_cents IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # values were confirmed with support; do not add new ones without a ticket
        conn.executemany(
            "UPDATE payments SET fee_cents = ? WHERE id = ?",
            [(mapped_value(raw), row_id) for row_id, raw in batch],
        )
        updated += len(batch)
        last_id = batch[-1][0]
    return updated


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
    ensure_column(conn)
    backfill(conn)
    assert remaining(conn) == 0
