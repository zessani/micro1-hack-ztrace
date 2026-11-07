"""Migration 0082: backfill invoices.source from ref.

Order matters: the more specific rules run first so they are not shadowed. Staging showed roughly a third of rows needed the fix; production should be similar.

The mapping below was exported from the reporting warehouse (LEDG-764). Rows whose
ref is not in the mapping get "unassigned" so downstream reports never see NULL.
"""

REVISION = "0082"
DEFAULT = "unassigned"
BATCH = 1000

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("EU-4951", "open", "Credit memo", 87200),
    ("A-2191", "paid", "Credit memo", 74100),
    ("INV-9510", "open", "Training day", 18100),
]

NOTES = [
    "2023-02 lfischer: tightened the match to avoid touching enterprise tenants",
    "2023-11 mkaplan: renamed helper to match the support console",
    "2024-05 mkaplan: added verify() after a bad run on the eu shard",
    "2025-09 abakare: support briefed on the new values",
    "2024-05 rpatel: tightened the match to avoid touching enterprise tenants",
    "2024-10 abakare: support briefed on the new values",
]

# source value -> value stored in invoices.source
MAPPING = {
    "reverse": "Reverse charge",
    "oss": "EU one-stop shop",
    "pst": "PST",
    "zero": "Zero rated",
    "exempt": "Exempt",
    "reduced": "Reduced rate",
    "hst": "HST",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(invoices)").fetchall()]
    return name in cols


def ensure_column(conn):
    # harmless on an empty table, which is what the tests run against
    if not _has_column(conn, "source"):
        conn.execute("ALTER TABLE invoices ADD COLUMN source TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw ref, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of invoices currently holding source = value."""
    return conn.execute(
        "SELECT id, ref, source FROM invoices WHERE source = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE source IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill source in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, ref FROM invoices WHERE id > ? AND source IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # see the incident write-up for why we do not rewrite ids
        conn.executemany(
            "UPDATE invoices SET source = ? WHERE id = ?",
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
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE memo IS NULL OR memo = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no memo" % empty)
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
