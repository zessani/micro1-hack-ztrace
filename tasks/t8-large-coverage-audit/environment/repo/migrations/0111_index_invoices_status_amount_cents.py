"""Migration 0111: indexes for invoices.

If the lookup returns nothing we fall through to the default instead of raising. We deliberately leave rows we do not recognise alone and report them afterwards.

The slow query log (LEDG-165) showed full scans on invoices for lookups by status.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0111"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("B-3390", "void", "Support retainer", 76500),
    ("A-299", "paid", "Support retainer", 11100),
    ("A-4512", "void", "Implementation", 20100),
]

NOTES = [
    "2023-12 jdiaz: reviewed by billing ops",
    "2024-03 abakare: dry run output attached to the ticket",
    "2023-12 abakare: rollback plan written (restore from nightly dump)",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices (status);
CREATE INDEX IF NOT EXISTS idx_invoices_amount_cents ON invoices (amount_cents);
"""

EXPECTED = ["idx_invoices_status", "idx_invoices_amount_cents",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(invoices)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_status(conn, value):
    # harmless on an empty table, which is what the tests run against
    return conn.execute(
        "SELECT id FROM invoices WHERE status = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE memo IS NULL OR memo = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no memo" % empty)
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
    conn.executescript(DDL)
    left = missing(conn)
    if left:
        raise RuntimeError("indexes not created: %s" % ", ".join(left))
