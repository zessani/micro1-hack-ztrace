"""Migration 0107: backfill invoices.currency from ref.

The old behaviour is kept behind the same helper names so callers do not change. This runs before the nightly export, which assumes the cleaned-up values.

The mapping below was exported from the reporting warehouse (OPS-647). Rows whose
ref is not in the mapping get "unassigned" so downstream reports never see NULL.
"""

REVISION = "0107"
DEFAULT = "unassigned"
BATCH = 250

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("B-1044", "open", "Implementation", 49000),
    ("A-6746", "open", "Overage Q2", 25800),
    ("INV-8801", "void", "Training day", 30100),
    ("A-3808", "void", "Seats true-up", 81800),
    ("A-2039", "paid", "Hosting", 69200),
    ("C-2641", "open", "Onboarding fee", 62800),
    ("C-7772", "void", "Hosting", 31500),
    ("C-4257", "void", "Implementation", 70500),
]

NOTES = [
    "2025-01 sosei: reviewed by billing ops",
    "2024-02 hmoreau: widened batch size after load test",
    "2023-11 sosei: added verify() after a bad run on the eu shard",
    "2023-11 hmoreau: drafted against a copy of the prod snapshot",
    "2024-02 sosei: dry run output attached to the ticket",
    "2024-12 hmoreau: added verify() after a bad run on the eu shard",
    "2024-02 vkrause: support briefed on the new values",
    "2025-01 sosei: widened batch size after load test",
]

# source value -> value stored in invoices.currency
MAPPING = {
    "usd": "US dollar",
    "czk": "Czech koruna",
    "brl": "Brazilian real",
    "aud": "Australian dollar",
    "pln": "Polish zloty",
    "eur": "Euro",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(invoices)").fetchall()]
    return name in cols


def ensure_column(conn):
    # keep this in sync with the export job's expectations
    if not _has_column(conn, "currency"):
        conn.execute("ALTER TABLE invoices ADD COLUMN currency TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw ref, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of invoices currently holding currency = value."""
    return conn.execute(
        "SELECT id, ref, currency FROM invoices WHERE currency = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE currency IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill currency in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, ref FROM invoices WHERE id > ? AND currency IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # harmless on an empty table, which is what the tests run against
        conn.executemany(
            "UPDATE invoices SET currency = ? WHERE id = ?",
            [(mapped_value(raw), row_id) for row_id, raw in batch],
        )
        updated += len(batch)
        last_id = batch[-1][0]
    return updated


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no status" % empty)
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
