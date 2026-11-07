"""Migration 0096: reference table ref_currency_codes_additions.

This runs before the nightly export, which assumes the cleaned-up values. Order matters: the more specific rules run first so they are not shadowed.

Source of truth is the shared spreadsheet owned by Finance ops (BILL-737). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0096"

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("hmoreau", "tax id missing"),
    ("cwu", "card expired"),
    ("tnguyen", "refund issued, see ticket"),
    ("abakare", "wants invoice resent"),
    ("abakare", "requested PO number on invoices"),
    ("cwu", "asked for W-9"),
    ("vkrause", "contract renewal pending"),
    ("vkrause", "chargeback opened by bank"),
    ("tnguyen", "customer unreachable"),
    ("jdiaz", "tax id missing"),
    ("lfischer", "chargeback opened by bank"),
    ("sosei", "card expired"),
    ("mkaplan", "contract renewal pending"),
    ("abakare", "address changed"),
    ("tnguyen", "called about duplicate charge"),
    ("sosei", "tax id missing"),
    ("mkaplan", "payment plan agreed"),
    ("cwu", "requested PO number on invoices"),
    ("mkaplan", "wants invoice resent"),
    ("cwu", "customer unreachable"),
    ("sosei", "card expired"),
    ("sosei", "payment plan agreed"),
    ("tnguyen", "asked for W-9"),
    ("hmoreau", "tax id missing"),
    ("rpatel", "moved to annual plan"),
    ("sosei", "card expired"),
    ("vkrause", "asked for W-9"),
    ("mkaplan", "contract renewal pending"),
    ("vkrause", "customer unreachable"),
    ("jdiaz", "chargeback opened by bank"),
    ("mkaplan", "asked for W-9"),
    ("hmoreau", "called about duplicate charge"),
    ("hmoreau", "address changed"),
    ("vkrause", "wants invoice resent"),
    ("mkaplan", "escalated to finance"),
    ("vkrause", "moved to annual plan"),
]

NOTES = [
    "2023-11 sosei: widened batch size after load test",
    "2024-04 sosei: tightened the match to avoid touching enterprise tenants",
    "2024-11 lfischer: reviewed by billing ops",
    "2023-08 lfischer: drafted against a copy of the prod snapshot",
    "2025-03 rpatel: rehearsed on staging, 6195 rows touched",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_currency_codes_additions (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("GBP", "Pound sterling", 0, 1),
    ("HKD", "Hong Kong dollar", 10, 1),
    ("SGD", "Singapore dollar", 20, 1),
    ("EUR", "Euro", 30, 0),
    ("SEK", "Swedish krona", 40, 1),
    ("PLN", "Polish zloty", 50, 1),
    ("TRY", "Turkish lira", 60, 1),
    ("AED", "UAE dirham", 70, 1),
    ("ZAR", "South African rand", 80, 1),
    ("DKK", "Danish krone", 90, 1),
    ("INR", "Indian rupee", 100, 1),
    ("CZK", "Czech koruna", 110, 0),
    ("NZD", "New Zealand dollar", 120, 1),
    ("BRL", "Brazilian real", 130, 0),
    ("USD", "US dollar", 140, 0),
    ("CAD", "Canadian dollar", 150, 1),
    ("KRW", "South Korean won", 160, 1),
    ("AUD", "Australian dollar", 170, 1),
    ("JPY", "Japanese yen", 180, 1),
    ("ILS", "Israeli shekel", 190, 1),
    ("CHF", "Swiss franc", 200, 1),
    ("NOK", "Norwegian krone", 210, 1),
    ("MXN", "Mexican peso", 220, 1),
    ("CNY", "Chinese yuan", 230, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_currency_codes_additions WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # harmless on an empty table, which is what the tests run against
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_currency_codes_additions WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_currency_codes_additions WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE body IS NULL OR body = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no body" % empty)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    lines = ["notes: %d rows" % total]
    for problem in verify(conn):
        lines.append("  ! " + problem)
    if len(lines) == 1:
        lines.append("  ok")
    return lines


def upgrade(conn):
    conn.executescript(DDL)
    conn.executemany(
        "INSERT OR IGNORE INTO ref_currency_codes_additions (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
