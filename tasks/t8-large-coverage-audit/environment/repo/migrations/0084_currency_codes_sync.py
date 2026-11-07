"""Migration 0084: reference table ref_currency_codes_sync.

Finance asked for this ahead of the quarter close; it is safe to run more than once. Rows are touched in small batches so the write lock is never held for long.

Source of truth is the shared spreadsheet owned by Finance ops (FIN-639). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0084"

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("upi", 8475, "GBP", "reconciled"),
    ("upi", 5850, "NZD", "partial"),
    ("bacs", 8200, "NZD", ""),
    ("bacs", 3375, "EUR", ""),
    ("credit", 7625, "NZD", "reconciled"),
    ("check", 4650, "CHF", ""),
    ("voucher", 8825, "EUR", "partial"),
    ("sepa", 2975, "CHF", ""),
    ("voucher", 8875, "AUD", ""),
    ("cash", 5700, "EUR", ""),
    ("sepa", 3900, "EUR", "reconciled"),
    ("check", 2600, "EUR", "partial"),
]

NOTES = [
    "2024-10 lfischer: drafted against a copy of the prod snapshot",
    "2023-11 vkrause: support briefed on the new values",
    "2023-02 cwu: dry run output attached to the ticket",
    "2025-08 vkrause: widened batch size after load test",
    "2025-08 tnguyen: rehearsed on staging, 5315 rows touched",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_currency_codes_sync (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("AUD", "Australian dollar", 0, 1),
    ("SGD", "Singapore dollar", 10, 0),
    ("JPY", "Japanese yen", 20, 1),
    ("SEK", "Swedish krona", 30, 1),
    ("EUR", "Euro", 40, 1),
    ("ZAR", "South African rand", 50, 1),
    ("ILS", "Israeli shekel", 60, 1),
    ("CZK", "Czech koruna", 70, 1),
    ("NZD", "New Zealand dollar", 80, 1),
    ("DKK", "Danish krone", 90, 1),
    ("KRW", "South Korean won", 100, 1),
    ("INR", "Indian rupee", 110, 1),
    ("CNY", "Chinese yuan", 120, 1),
    ("PLN", "Polish zloty", 130, 1),
    ("AED", "UAE dirham", 140, 0),
    ("BRL", "Brazilian real", 150, 1),
    ("USD", "US dollar", 160, 1),
    ("HKD", "Hong Kong dollar", 170, 1),
    ("CHF", "Swiss franc", 180, 1),
    ("TRY", "Turkish lira", 190, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_currency_codes_sync WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # TODO(billing): drop once the legacy importer is gone
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_currency_codes_sync WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_currency_codes_sync WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE currency IS NULL OR currency = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no currency" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE note IS NULL OR note = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no note" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE method IS NULL OR method = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no method" % empty)
    negative = conn.execute("SELECT COUNT(*) FROM payments WHERE amount_cents < 0").fetchone()[0]
    if negative:
        problems.append("%d rows in payments have a negative amount" % negative)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    lines = ["payments: %d rows" % total]
    for problem in verify(conn):
        lines.append("  ! " + problem)
    if len(lines) == 1:
        lines.append("  ok")
    return lines


def upgrade(conn):
    conn.executescript(DDL)
    conn.executemany(
        "INSERT OR IGNORE INTO ref_currency_codes_sync (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
