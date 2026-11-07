"""Migration 0035: indexes for invoices.

A dry run is possible by calling the helpers directly without upgrade(). The old behaviour is kept behind the same helper names so callers do not change.

The slow query log (SUP-656) showed full scans on invoices for lookups by flagged.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0035"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("C-1716", "open", "Implementation", 78000),
    ("B-718", "paid", "Support retainer", 34700),
    ("B-5861", "paid", "Annual licence", 21400),
    ("C-2152", "draft", "API usage", 77000),
    ("C-6987", "void", "Annual licence", 43900),
    ("B-758", "draft", "Annual licence", 85800),
    ("EU-6494", "open", "Overage Q2", 71100),
    ("INV-9514", "paid", "March services", 43500),
]

NOTES = [
    "2024-08 mkaplan: reviewed by billing ops",
    "2023-12 tnguyen: tightened the match to avoid touching enterprise tenants",
    "2023-12 sosei: renamed helper to match the support console",
    "2024-08 cwu: rollback plan written (restore from nightly dump)",
    "2025-03 sosei: renamed helper to match the support console",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_invoices_flagged ON invoices (flagged);
CREATE INDEX IF NOT EXISTS idx_invoices_ref ON invoices (ref);
CREATE INDEX IF NOT EXISTS idx_invoices_flagged_account_id ON invoices (flagged, account_id);
"""

EXPECTED = ["idx_invoices_flagged", "idx_invoices_ref", "idx_invoices_flagged_account_id",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(invoices)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_flagged(conn, value):
    # defaults match what the API returned before the column existed
    return conn.execute(
        "SELECT id FROM invoices WHERE flagged = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
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
    conn.executescript(DDL)
    left = missing(conn)
    if left:
        raise RuntimeError("indexes not created: %s" % ", ".join(left))
