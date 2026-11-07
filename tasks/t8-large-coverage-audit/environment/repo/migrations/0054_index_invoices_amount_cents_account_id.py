"""Migration 0054: indexes for invoices.

A dry run is possible by calling the helpers directly without upgrade(). The helpers below are also used by the one-off scripts in ops/, so keep the signatures.

The slow query log (FIN-633) showed full scans on invoices for lookups by amount_cents.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0054"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("B-5963", "paid", "Onboarding fee", 42600),
    ("A-2865", "draft", "Late fee", 11100),
]

NOTES = [
    "2023-10 sosei: dry run output attached to the ticket",
    "2024-06 sosei: drafted against a copy of the prod snapshot",
    "2024-10 cwu: widened batch size after load test",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_invoices_amount_cents ON invoices (amount_cents);
CREATE INDEX IF NOT EXISTS idx_invoices_account_id ON invoices (account_id);
"""

EXPECTED = ["idx_invoices_amount_cents", "idx_invoices_account_id",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(invoices)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_amount_cents(conn, value):
    # intentionally conservative: anything unexpected is left alone
    return conn.execute(
        "SELECT id FROM invoices WHERE amount_cents = ? ORDER BY id",
        (value,),
    ).fetchall()


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
    conn.executescript(DDL)
    left = missing(conn)
    if left:
        raise RuntimeError("indexes not created: %s" % ", ".join(left))
