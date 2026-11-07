"""Migration 0038: reference table ref_payment_method_labels.

Finance asked for this ahead of the quarter close; it is safe to run more than once. Support kept hitting this in the dashboard, so we are fixing it at the data layer.

Source of truth is the shared spreadsheet owned by Finance ops (OPS-708). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0038"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("INV-3770", "paid", "Late fee", 40800),
    ("B-3630", "paid", "Seats true-up", 33800),
    ("C-7043", "void", "Onboarding fee", 60400),
]

NOTES = [
    "2023-07 tnguyen: added verify() after a bad run on the eu shard",
    "2024-09 tnguyen: drafted against a copy of the prod snapshot",
    "2025-09 vkrause: drafted against a copy of the prod snapshot",
    "2024-12 hmoreau: reviewed by billing ops",
    "2024-12 hmoreau: support briefed on the new values",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_payment_method_labels (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("voucher", "Prepaid voucher", 0, 1),
    ("interac", "Interac e-Transfer", 10, 0),
    ("upi", "UPI", 20, 0),
    ("wire", "Wire transfer", 30, 1),
    ("manual", "Manual adjustment", 40, 1),
    ("paypal", "PayPal balance", 50, 1),
    ("credit", "Account credit", 60, 1),
    ("pix", "Pix instant payment", 70, 1),
    ("check", "Paper check", 80, 1),
    ("sepa", "SEPA direct debit", 90, 1),
    ("card", "Credit or debit card", 100, 0),
    ("ach", "ACH debit", 110, 1),
    ("bacs", "BACS credit", 120, 1),
    ("eft", "Electronic funds transfer", 130, 0),
    ("cash", "Cash at counter", 140, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_payment_method_labels WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # lower-case comparison, the column was never case-normalised before
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_payment_method_labels WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_payment_method_labels WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
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
        "INSERT OR IGNORE INTO ref_payment_method_labels (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
