"""Migration 0024: backfill invoices.tax_category from memo.

This runs before the nightly export, which assumes the cleaned-up values. Support kept hitting this in the dashboard, so we are fixing it at the data layer.

The mapping below was exported from the reporting warehouse (SUP-221). Rows whose
memo is not in the mapping get "other" so downstream reports never see NULL.
"""

REVISION = "0024"
DEFAULT = "other"
BATCH = 250

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("B-3154", "void", "Implementation", 64800),
    ("C-6475", "void", "Onboarding fee", 89400),
    ("A-9191", "void", "Onboarding fee", 89700),
]

NOTES = [
    "2024-11 abakare: rehearsed on staging, 4046 rows touched",
    "2023-05 tnguyen: renamed helper to match the support console",
    "2024-11 tnguyen: drafted against a copy of the prod snapshot",
    "2025-07 hmoreau: support briefed on the new values",
]

# source value -> value stored in invoices.tax_category
MAPPING = {
    "pst": "PST",
    "reverse": "Reverse charge",
    "reduced": "Reduced rate",
    "standard": "Standard rate",
    "exempt": "Exempt",
    "zero": "Zero rated",
    "gst": "GST",
    "hst": "HST",
    "oss": "EU one-stop shop",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(invoices)").fetchall()]
    return name in cols


def ensure_column(conn):
    # TODO(billing): drop once the legacy importer is gone
    if not _has_column(conn, "tax_category"):
        conn.execute("ALTER TABLE invoices ADD COLUMN tax_category TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw memo, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of invoices currently holding tax_category = value."""
    return conn.execute(
        "SELECT id, memo, tax_category FROM invoices WHERE tax_category = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE tax_category IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill tax_category in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, memo FROM invoices WHERE id > ? AND tax_category IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # harmless on an empty table, which is what the tests run against
        conn.executemany(
            "UPDATE invoices SET tax_category = ? WHERE id = ?",
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
