"""Migration 0086: reference table ref_payment_method_labels_v2.

Support kept hitting this in the dashboard, so we are fixing it at the data layer. This runs before the nightly export, which assumes the cleaned-up values.

Source of truth is the shared spreadsheet owned by Finance ops (OPS-974). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0086"

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("eft", 2525, "CHF", "second instalment"),
    ("eft", 1800, "CHF", "partial"),
    ("pix", 9900, "NZD", "second instalment"),
    ("manual", 5825, "AUD", "second instalment"),
    ("paypal", 7050, "GBP", "partial"),
    ("ach", 2200, "CHF", "reconciled"),
]

NOTES = [
    "2024-10 hmoreau: dry run output attached to the ticket",
    "2023-08 lfischer: tightened the match to avoid touching enterprise tenants",
    "2023-12 vkrause: rehearsed on staging, 211 rows touched",
    "2024-06 abakare: drafted against a copy of the prod snapshot",
    "2023-12 abakare: dry run output attached to the ticket",
    "2024-10 lfischer: rehearsed on staging, 211 rows touched",
    "2025-03 abakare: rehearsed on staging, 211 rows touched",
    "2024-06 hmoreau: added verify() after a bad run on the eu shard",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_payment_method_labels_v2 (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("upi", "UPI", 0, 1),
    ("sepa", "SEPA direct debit", 10, 1),
    ("check", "Paper check", 20, 1),
    ("wire", "Wire transfer", 30, 1),
    ("cash", "Cash at counter", 40, 0),
    ("ach", "ACH debit", 50, 1),
    ("bacs", "BACS credit", 60, 1),
    ("interac", "Interac e-Transfer", 70, 0),
    ("credit", "Account credit", 80, 1),
    ("paypal", "PayPal balance", 90, 1),
    ("manual", "Manual adjustment", 100, 1),
    ("pix", "Pix instant payment", 110, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_payment_method_labels_v2 WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # keep this in sync with the export job's expectations
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_payment_method_labels_v2 WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_payment_method_labels_v2 WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE method IS NULL OR method = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no method" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE note IS NULL OR note = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no note" % empty)
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
        "INSERT OR IGNORE INTO ref_payment_method_labels_v2 (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
