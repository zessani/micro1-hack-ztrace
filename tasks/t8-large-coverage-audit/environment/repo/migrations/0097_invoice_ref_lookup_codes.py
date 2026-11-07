"""Migration 0097: reference table ref_currency_codes_update.

Finance asked for this ahead of the quarter close; it is safe to run more than once. If the lookup returns nothing we fall through to the default instead of raising.

Source of truth is the shared spreadsheet owned by Finance ops (OPS-557). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0097"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("A-807", "void", "Overage Q2", 44600),
    ("A-4572", "draft", "Hosting", 31200),
    ("A-7367", "open", "Late fee", 76600),
    ("A-9708", "paid", "Onboarding fee", 66500),
    ("C-7702", "open", "Implementation", 29900),
    ("B-7049", "paid", "API usage", 15300),
    ("EU-4618", "void", "Late fee", 82500),
    ("INV-1516", "void", "Annual licence", 26400),
    ("EU-780", "void", "Implementation", 18100),
    ("B-7467", "paid", "Credit memo", 27000),
    ("A-3075", "draft", "Implementation", 89000),
    ("B-4090", "draft", "Implementation", 21400),
    ("B-6236", "paid", "API usage", 5100),
    ("A-4603", "open", "Credit memo", 56600),
    ("C-4795", "open", "Onboarding fee", 17200),
    ("C-8146", "open", "Seats true-up", 30700),
]

NOTES = [
    "2024-10 vkrause: widened batch size after load test",
    "2024-09 vkrause: dry run output attached to the ticket",
    "2023-06 rpatel: added verify() after a bad run on the eu shard",
    "2023-12 rpatel: reviewed by billing ops",
    "2023-12 mkaplan: tightened the match to avoid touching enterprise tenants",
    "2024-09 vkrause: widened batch size after load test",
    "2025-02 mkaplan: renamed helper to match the support console",
    "2023-12 mkaplan: dry run output attached to the ticket",
    "2024-10 tnguyen: reviewed by billing ops",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_currency_codes_update (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("MXN", "Mexican peso", 0, 1),
    ("ZAR", "South African rand", 10, 1),
    ("EUR", "Euro", 20, 1),
    ("TRY", "Turkish lira", 30, 0),
    ("CAD", "Canadian dollar", 40, 1),
    ("CZK", "Czech koruna", 50, 1),
    ("PLN", "Polish zloty", 60, 0),
    ("ILS", "Israeli shekel", 70, 1),
    ("SEK", "Swedish krona", 80, 1),
    ("AUD", "Australian dollar", 90, 0),
    ("JPY", "Japanese yen", 100, 1),
    ("NOK", "Norwegian krone", 110, 1),
    ("AED", "UAE dirham", 120, 1),
    ("BRL", "Brazilian real", 130, 1),
    ("NZD", "New Zealand dollar", 140, 1),
    ("INR", "Indian rupee", 150, 1),
    ("CHF", "Swiss franc", 160, 0),
    ("KRW", "South Korean won", 170, 1),
    ("DKK", "Danish krone", 180, 1),
    ("USD", "US dollar", 190, 0),
    ("GBP", "Pound sterling", 200, 1),
    ("SGD", "Singapore dollar", 210, 1),
    ("CNY", "Chinese yuan", 220, 0),
    ("HKD", "Hong Kong dollar", 230, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_currency_codes_update WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # harmless on an empty table, which is what the tests run against
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_currency_codes_update WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_currency_codes_update WHERE code = ?", (code,)).fetchone()
    return row is not None


def _eq(column, value):
    """One equality condition, ready to append to a WHERE clause."""
    return " AND %s = '%s'" % (column, value)


def find_invoice(conn, ref):
    """Invoices with a given reference (support console)."""
    sql = "SELECT id, ref, status FROM invoices WHERE status IS NOT NULL"
    sql += _eq("ref", ref)
    return conn.execute(sql).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no status" % empty)
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
    conn.executemany(
        "INSERT OR IGNORE INTO ref_currency_codes_update (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
