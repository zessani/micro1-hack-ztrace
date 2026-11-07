"""Migration 0093: reference table ref_payment_method_labels_update.

Finance asked for this ahead of the quarter close; it is safe to run more than once. The change is idempotent: rerunning on an already migrated database is a no-op.

Source of truth is the shared spreadsheet owned by Finance ops (LEDG-654). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0093"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("A-9190", "open", "Onboarding fee", 10300),
    ("C-3439", "draft", "Credit memo", 84100),
    ("A-4501", "void", "Implementation", 18900),
    ("C-5309", "paid", "Onboarding fee", 25200),
    ("A-4180", "draft", "Support retainer", 55300),
]

NOTES = [
    "2024-10 vkrause: drafted against a copy of the prod snapshot",
    "2023-06 lfischer: dry run output attached to the ticket",
    "2025-08 vkrause: added verify() after a bad run on the eu shard",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_payment_method_labels_update (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("upi", "UPI", 0, 1),
    ("paypal", "PayPal balance", 10, 0),
    ("ach", "ACH debit", 20, 1),
    ("pix", "Pix instant payment", 30, 1),
    ("eft", "Electronic funds transfer", 40, 1),
    ("voucher", "Prepaid voucher", 50, 1),
    ("wire", "Wire transfer", 60, 1),
    ("check", "Paper check", 70, 1),
    ("credit", "Account credit", 80, 0),
    ("card", "Credit or debit card", 90, 1),
    ("interac", "Interac e-Transfer", 100, 1),
    ("cash", "Cash at counter", 110, 0),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_payment_method_labels_update WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # values were confirmed with support; do not add new ones without a ticket
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_payment_method_labels_update WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_payment_method_labels_update WHERE code = ?", (code,)).fetchone()
    return row is not None


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
    conn.executemany(
        "INSERT OR IGNORE INTO ref_payment_method_labels_update (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
