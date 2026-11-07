"""Migration 0066: reference table ref_currency_codes_v2.

The old behaviour is kept behind the same helper names so callers do not change. A dry run is possible by calling the helpers directly without upgrade().

Source of truth is the shared spreadsheet owned by Finance ops (OPS-639). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0066"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("C-433", "paid", "Onboarding fee", 55300),
    ("C-4985", "void", "Training day", 71900),
    ("EU-6760", "paid", "Late fee", 86200),
    ("INV-913", "void", "Training day", 61000),
    ("EU-5143", "open", "Overage Q2", 60000),
    ("EU-9721", "void", "Late fee", 7900),
    ("EU-6658", "draft", "Training day", 78500),
    ("C-6616", "open", "Implementation", 11200),
]

NOTES = [
    "2024-08 rpatel: dry run output attached to the ticket",
    "2023-08 hmoreau: dry run output attached to the ticket",
    "2024-08 jdiaz: rollback plan written (restore from nightly dump)",
    "2025-06 jdiaz: reviewed by billing ops",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_currency_codes_v2 (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("NOK", "Norwegian krone", 0, 0),
    ("ZAR", "South African rand", 10, 0),
    ("GBP", "Pound sterling", 20, 1),
    ("CHF", "Swiss franc", 30, 0),
    ("CZK", "Czech koruna", 40, 1),
    ("TRY", "Turkish lira", 50, 0),
    ("HKD", "Hong Kong dollar", 60, 1),
    ("KRW", "South Korean won", 70, 0),
    ("EUR", "Euro", 80, 1),
    ("BRL", "Brazilian real", 90, 1),
    ("CNY", "Chinese yuan", 100, 1),
    ("MXN", "Mexican peso", 110, 1),
    ("SGD", "Singapore dollar", 120, 1),
    ("AUD", "Australian dollar", 130, 0),
    ("NZD", "New Zealand dollar", 140, 1),
    ("SEK", "Swedish krona", 150, 1),
    ("USD", "US dollar", 160, 1),
    ("ILS", "Israeli shekel", 170, 1),
    ("CAD", "Canadian dollar", 180, 1),
    ("DKK", "Danish krone", 190, 0),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_currency_codes_v2 WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # lower-case comparison, the column was never case-normalised before
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_currency_codes_v2 WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_currency_codes_v2 WHERE code = ?", (code,)).fetchone()
    return row is not None


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
        "INSERT OR IGNORE INTO ref_currency_codes_v2 (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
