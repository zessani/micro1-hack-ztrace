"""Migration 0071: indexes for invoices.

Support kept hitting this in the dashboard, so we are fixing it at the data layer. If the lookup returns nothing we fall through to the default instead of raising.

The slow query log (FIN-813) showed full scans on invoices for lookups by account_id.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0071"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("A-3398", "paid", "Seats true-up", 67500),
    ("A-7217", "void", "Hosting", 40500),
    ("EU-4210", "draft", "Onboarding fee", 8100),
    ("EU-7093", "void", "Late fee", 35400),
    ("C-9109", "void", "Implementation", 77100),
    ("INV-9055", "open", "Support retainer", 39500),
    ("C-5151", "paid", "Credit memo", 55500),
    ("INV-622", "open", "March services", 20400),
    ("EU-8094", "paid", "Credit memo", 46200),
    ("INV-6429", "draft", "Training day", 81600),
    ("EU-2202", "open", "March services", 600),
    ("C-600", "void", "Annual licence", 14300),
    ("A-4029", "open", "Onboarding fee", 51200),
    ("B-6122", "void", "API usage", 81400),
    ("EU-4554", "void", "Hosting", 10500),
    ("B-8403", "open", "Late fee", 26400),
]

NOTES = [
    "2023-03 jdiaz: widened batch size after load test",
    "2023-03 jdiaz: support briefed on the new values",
    "2023-10 hmoreau: rollback plan written (restore from nightly dump)",
    "2023-10 jdiaz: rollback plan written (restore from nightly dump)",
    "2024-11 sosei: support briefed on the new values",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_invoices_account_id ON invoices (account_id);
CREATE INDEX IF NOT EXISTS idx_invoices_flagged ON invoices (flagged);
"""

EXPECTED = ["idx_invoices_account_id", "idx_invoices_flagged",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(invoices)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_account_id(conn, value):
    # harmless on an empty table, which is what the tests run against
    return conn.execute(
        "SELECT id FROM invoices WHERE account_id = ? ORDER BY id",
        (value,),
    ).fetchall()


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
    conn.executescript(DDL)
    left = missing(conn)
    if left:
        raise RuntimeError("indexes not created: %s" % ", ".join(left))
