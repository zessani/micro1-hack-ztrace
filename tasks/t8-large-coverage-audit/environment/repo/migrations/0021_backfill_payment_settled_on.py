"""Migration 0021: backfill payments.settled_on from method.

If the lookup returns nothing we fall through to the default instead of raising. Do not renumber this file; later migrations refer to its REVISION.

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("interac", 7100, "SEK", ""),
    ("cash", 7225, "AUD", ""),
]

NOTES = [
    "2023-08 hmoreau: dry run output attached to the ticket",
    "2023-08 tnguyen: tightened the match to avoid touching enterprise tenants",
    "2024-10 jdiaz: reviewed by billing ops",
]

The mapping below was exported from the reporting warehouse (SUP-775). Rows whose
method is not in the mapping get "unknown" so downstream reports never see NULL.
"""

REVISION = "0021"
DEFAULT = "unknown"
BATCH = 250

# source value -> value stored in payments.settled_on
MAPPING = {
    "ie": "Ireland",
    "cn": "China",
    "th": "Thailand",
    "nl": "Netherlands",
    "ph": "Philippines",
    "dk": "Denmark",
    "id": "Indonesia",
    "lu": "Luxembourg",
    "gb": "United Kingdom",
    "my": "Malaysia",
    "pl": "Poland",
    "pt": "Portugal",
    "hk": "Hong Kong",
    "ro": "Romania",
    "cl": "Chile",
    "pe": "Peru",
    "cz": "Czechia",
    "fi": "Finland",
    "ng": "Nigeria",
    "hu": "Hungary",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(payments)").fetchall()]
    return name in cols


def ensure_column(conn):
    # this used to be a single UPDATE but it locked the table for too long
    if not _has_column(conn, "settled_on"):
        conn.execute("ALTER TABLE payments ADD COLUMN settled_on TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw method, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of payments currently holding settled_on = value."""
    return conn.execute(
        "SELECT id, method, settled_on FROM payments WHERE settled_on = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE settled_on IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill settled_on in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, method FROM payments WHERE id > ? AND settled_on IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # NULL and empty string are both treated as 'missing' on purpose
        conn.executemany(
            "UPDATE payments SET settled_on = ? WHERE id = ?",
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
