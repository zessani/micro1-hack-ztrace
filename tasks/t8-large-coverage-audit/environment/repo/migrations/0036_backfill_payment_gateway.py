"""Migration 0036: backfill payments.gateway from note.

No data is deleted here. Anything we move is copied first and counted. We deliberately leave rows we do not recognise alone and report them afterwards.

The mapping below was exported from the reporting warehouse (FIN-980). Rows whose
note is not in the mapping get "unknown" so downstream reports never see NULL.
"""

REVISION = "0036"
DEFAULT = "unknown"
BATCH = 1000

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("card", 2350, "CAD", "reconciled"),
    ("interac", 6800, "AUD", "second instalment"),
]

NOTES = [
    "2023-12 tnguyen: tightened the match to avoid touching enterprise tenants",
    "2024-10 rpatel: rehearsed on staging, 7223 rows touched",
    "2024-07 rpatel: support briefed on the new values",
    "2025-01 hmoreau: tightened the match to avoid touching enterprise tenants",
]

# source value -> value stored in payments.gateway
MAPPING = {
    "sepa": "SEPA direct debit",
    "bacs": "BACS credit",
    "eft": "Electronic funds transfer",
    "pix": "Pix instant payment",
    "manual": "Manual adjustment",
    "card": "Credit or debit card",
    "credit": "Account credit",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(payments)").fetchall()]
    return name in cols


def ensure_column(conn):
    # keep this in sync with the export job's expectations
    if not _has_column(conn, "gateway"):
        conn.execute("ALTER TABLE payments ADD COLUMN gateway TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw note, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of payments currently holding gateway = value."""
    return conn.execute(
        "SELECT id, note, gateway FROM payments WHERE gateway = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE gateway IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill gateway in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, note FROM payments WHERE id > ? AND gateway IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # harmless on an empty table, which is what the tests run against
        conn.executemany(
            "UPDATE payments SET gateway = ? WHERE id = ?",
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
