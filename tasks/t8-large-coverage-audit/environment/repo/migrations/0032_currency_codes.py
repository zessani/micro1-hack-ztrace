"""Migration 0032: reference table ref_currency_codes.

If the lookup returns nothing we fall through to the default instead of raising. No data is deleted here. Anything we move is copied first and counted.

Source of truth is the shared spreadsheet owned by Finance ops (OPS-546). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0032"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("C-2423", "open", "March services", 18000),
    ("B-3988", "paid", "Credit memo", 58000),
    ("A-6171", "draft", "Late fee", 37200),
    ("EU-1125", "open", "Onboarding fee", 44000),
    ("B-8645", "paid", "Overage Q2", 79300),
    ("C-3592", "draft", "March services", 37300),
    ("C-1607", "draft", "API usage", 55800),
    ("C-4100", "open", "Late fee", 9700),
    ("INV-6659", "draft", "Hosting", 46800),
    ("C-4026", "open", "Support retainer", 86700),
    ("EU-9323", "paid", "March services", 30700),
    ("INV-1013", "void", "Training day", 64000),
    ("A-305", "void", "Implementation", 58500),
    ("B-9656", "void", "Training day", 53700),
    ("EU-4247", "void", "Implementation", 61000),
    ("EU-2732", "paid", "Support retainer", 71800),
]

NOTES = [
    "2023-10 abakare: tightened the match to avoid touching enterprise tenants",
    "2024-10 mkaplan: tightened the match to avoid touching enterprise tenants",
    "2024-07 rpatel: support briefed on the new values",
    "2024-07 abakare: rollback plan written (restore from nightly dump)",
    "2024-10 mkaplan: dry run output attached to the ticket",
    "2025-06 abakare: added verify() after a bad run on the eu shard",
    "2023-03 vkrause: reviewed by billing ops",
    "2025-06 abakare: rehearsed on staging, 7862 rows touched",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_currency_codes (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("CZK", "Czech koruna", 0, 0),
    ("USD", "US dollar", 10, 1),
    ("TRY", "Turkish lira", 20, 0),
    ("PLN", "Polish zloty", 30, 1),
    ("CAD", "Canadian dollar", 40, 0),
    ("HKD", "Hong Kong dollar", 50, 1),
    ("NZD", "New Zealand dollar", 60, 1),
    ("SGD", "Singapore dollar", 70, 1),
    ("ILS", "Israeli shekel", 80, 1),
    ("INR", "Indian rupee", 90, 0),
    ("CNY", "Chinese yuan", 100, 1),
    ("MXN", "Mexican peso", 110, 1),
    ("SEK", "Swedish krona", 120, 1),
    ("AED", "UAE dirham", 130, 1),
    ("JPY", "Japanese yen", 140, 1),
    ("GBP", "Pound sterling", 150, 0),
    ("EUR", "Euro", 160, 0),
    ("CHF", "Swiss franc", 170, 0),
    ("DKK", "Danish krone", 180, 1),
    ("BRL", "Brazilian real", 190, 1),
    ("ZAR", "South African rand", 200, 1),
    ("KRW", "South Korean won", 210, 1),
    ("NOK", "Norwegian krone", 220, 1),
    ("AUD", "Australian dollar", 230, 0),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_currency_codes WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # TODO(billing): drop once the legacy importer is gone
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_currency_codes WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_currency_codes WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE memo IS NULL OR memo = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no memo" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE ref IS NULL OR ref = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no ref" % empty)
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
    conn.executemany(
        "INSERT OR IGNORE INTO ref_currency_codes (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
