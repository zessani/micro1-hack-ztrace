"""Migration 0062: backfill invoices.po_number from status.

The old behaviour is kept behind the same helper names so callers do not change. A dry run is possible by calling the helpers directly without upgrade().

The mapping below was exported from the reporting warehouse (SUP-442). Rows whose
status is not in the mapping get "unassigned" so downstream reports never see NULL.
"""

REVISION = "0062"
DEFAULT = "unassigned"
BATCH = 500

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("INV-6472", "void", "Hosting", 79300),
    ("INV-2387", "void", "Hosting", 37400),
    ("EU-1227", "paid", "Support retainer", 53400),
    ("A-2895", "draft", "Overage Q2", 89200),
    ("INV-3169", "void", "Overage Q2", 34000),
]

NOTES = [
    "2023-07 hmoreau: rollback plan written (restore from nightly dump)",
    "2023-11 jdiaz: support briefed on the new values",
    "2024-08 abakare: drafted against a copy of the prod snapshot",
    "2024-11 jdiaz: rehearsed on staging, 2749 rows touched",
    "2024-08 jdiaz: widened batch size after load test",
    "2024-11 hmoreau: tightened the match to avoid touching enterprise tenants",
    "2025-08 hmoreau: renamed helper to match the support console",
]

# source value -> value stored in invoices.po_number
MAPPING = {
    "czk": "Czech koruna",
    "dkk": "Danish krone",
    "usd": "US dollar",
    "brl": "Brazilian real",
    "sgd": "Singapore dollar",
    "sek": "Swedish krona",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(invoices)").fetchall()]
    return name in cols


def ensure_column(conn):
    # this used to be a single UPDATE but it locked the table for too long
    if not _has_column(conn, "po_number"):
        conn.execute("ALTER TABLE invoices ADD COLUMN po_number TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw status, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of invoices currently holding po_number = value."""
    return conn.execute(
        "SELECT id, status, po_number FROM invoices WHERE po_number = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE po_number IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill po_number in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, status FROM invoices WHERE id > ? AND po_number IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # see the incident write-up for why we do not rewrite ids
        conn.executemany(
            "UPDATE invoices SET po_number = ? WHERE id = ?",
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
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE memo IS NULL OR memo = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no memo" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no status" % empty)
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
