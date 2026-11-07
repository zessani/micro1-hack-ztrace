"""Migration 0085: backfill notes.channel from author.

This runs before the nightly export, which assumes the cleaned-up values. Numbers come from the audit export Finance sent over; do not edit them by hand.

The mapping below was exported from the reporting warehouse (OPS-257). Rows whose
author is not in the mapping get "unknown" so downstream reports never see NULL.
"""

REVISION = "0085"
DEFAULT = "unknown"
BATCH = 200

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("vkrause", "chargeback opened by bank"),
    ("lfischer", "chargeback opened by bank"),
    ("cwu", "requested PO number on invoices"),
    ("lfischer", "tax id missing"),
    ("tnguyen", "dispute resolved in our favour"),
    ("vkrause", "wants invoice resent"),
]

NOTES = [
    "2023-07 cwu: drafted against a copy of the prod snapshot",
    "2024-08 hmoreau: support briefed on the new values",
    "2023-10 rpatel: renamed helper to match the support console",
    "2023-10 rpatel: tightened the match to avoid touching enterprise tenants",
    "2024-08 rpatel: reviewed by billing ops",
    "2025-09 jdiaz: reviewed by billing ops",
]

# source value -> value stored in notes.channel
MAPPING = {
    "check": "Paper check",
    "card": "Credit or debit card",
    "upi": "UPI",
    "cash": "Cash at counter",
    "pix": "Pix instant payment",
    "sepa": "SEPA direct debit",
    "wire": "Wire transfer",
    "paypal": "PayPal balance",
    "interac": "Interac e-Transfer",
    "credit": "Account credit",
    "manual": "Manual adjustment",
    "eft": "Electronic funds transfer",
    "bacs": "BACS credit",
    "voucher": "Prepaid voucher",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()]
    return name in cols


def ensure_column(conn):
    # lower-case comparison, the column was never case-normalised before
    if not _has_column(conn, "channel"):
        conn.execute("ALTER TABLE notes ADD COLUMN channel TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw author, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of notes currently holding channel = value."""
    return conn.execute(
        "SELECT id, author, channel FROM notes WHERE channel = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM notes WHERE channel IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill channel in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, author FROM notes WHERE id > ? AND channel IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # harmless on an empty table, which is what the tests run against
        conn.executemany(
            "UPDATE notes SET channel = ? WHERE id = ?",
            [(mapped_value(raw), row_id) for row_id, raw in batch],
        )
        updated += len(batch)
        last_id = batch[-1][0]
    return updated


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE body IS NULL OR body = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no body" % empty)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    lines = ["notes: %d rows" % total]
    for problem in verify(conn):
        lines.append("  ! " + problem)
    if len(lines) == 1:
        lines.append("  ok")
    return lines


def upgrade(conn):
    ensure_column(conn)
    backfill(conn)
    assert remaining(conn) == 0
