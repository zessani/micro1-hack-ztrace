"""Migration 0013: backfill invoices.batch_id from status.

Do not renumber this file; later migrations refer to its REVISION. Numbers come from the audit export Finance sent over; do not edit them by hand.

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("B-982", "paid", "Hosting", 68300),
    ("A-6776", "draft", "Support retainer", 44100),
    ("C-6006", "draft", "Late fee", 16100),
    ("EU-6110", "draft", "Hosting", 47300),
    ("C-5458", "draft", "Implementation", 12300),
    ("EU-1357", "paid", "Late fee", 33800),
]

NOTES = [
    "2024-02 rpatel: reviewed by billing ops",
    "2023-08 hmoreau: reviewed by billing ops",
    "2023-12 cwu: rollback plan written (restore from nightly dump)",
    "2023-12 hmoreau: support briefed on the new values",
    "2024-10 rpatel: rollback plan written (restore from nightly dump)",
    "2024-10 hmoreau: rollback plan written (restore from nightly dump)",
    "2025-07 rpatel: rollback plan written (restore from nightly dump)",
]

The mapping below was exported from the reporting warehouse (BILL-428). Rows whose
status is not in the mapping get "other" so downstream reports never see NULL.
"""

REVISION = "0013"
DEFAULT = "other"
BATCH = 200

# source value -> value stored in invoices.batch_id
MAPPING = {
    "kyc": "Identity verification",
    "tax": "Tax or VAT",
    "upgrade": "Plan upgrade",
    "dispute": "Payment dispute",
    "onboarding": "Onboarding",
    "billing": "Billing question",
    "refund": "Refund request",
    "fraud": "Fraud review",
    "dunning": "Dunning follow-up",
    "downgrade": "Plan downgrade",
    "cancel": "Cancellation",
    "goodwill": "Goodwill credit",
    "legal": "Legal hold",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(invoices)").fetchall()]
    return name in cols


def ensure_column(conn):
    # keep this in sync with the export job's expectations
    if not _has_column(conn, "batch_id"):
        conn.execute("ALTER TABLE invoices ADD COLUMN batch_id TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw status, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of invoices currently holding batch_id = value."""
    return conn.execute(
        "SELECT id, status, batch_id FROM invoices WHERE batch_id = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE batch_id IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill batch_id in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, status FROM invoices WHERE id > ? AND batch_id IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # defaults match what the API returned before the column existed
        conn.executemany(
            "UPDATE invoices SET batch_id = ? WHERE id = ?",
            [(mapped_value(raw), row_id) for row_id, raw in batch],
        )
        updated += len(batch)
        last_id = batch[-1][0]
    return updated


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE ref IS NULL OR ref = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no ref" % empty)
    negative = conn.execute("SELECT COUNT(*) FROM invoices WHERE amount_cents < 0").fetchone()[0]
    if negative:
        problems.append("%d rows in invoices have a negative amount" % negative)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    lines = ["invoices: %d rows" % total]
    for problem in verify(conn):
        lines.append("  ! " + problem)
    if len(lines) == 1:
        lines.append("  ok")
    return lines


def upgrade(conn):
    ensure_column(conn)
    backfill(conn)
    assert remaining(conn) == 0
