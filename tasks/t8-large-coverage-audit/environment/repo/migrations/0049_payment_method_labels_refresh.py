"""Migration 0049: reference table ref_payment_method_labels_refresh.

The change is idempotent: rerunning on an already migrated database is a no-op. Do not renumber this file; later migrations refer to its REVISION.

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ap.bluth@bluth.example", "Bluth Logistics", "default", "active"),
    ("ar.tyrell@tyrell.example", "Tyrell Health", "emea", "trial"),
]

NOTES = [
    "2023-06 sosei: reviewed by billing ops",
    "2024-11 rpatel: reviewed by billing ops",
    "2025-03 sosei: support briefed on the new values",
]

Source of truth is the shared spreadsheet owned by Finance ops (OPS-730). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0049"

DDL = """
CREATE TABLE IF NOT EXISTS ref_payment_method_labels_refresh (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("ach", "ACH debit", 0, 1),
    ("bacs", "BACS credit", 10, 1),
    ("eft", "Electronic funds transfer", 20, 0),
    ("credit", "Account credit", 30, 1),
    ("voucher", "Prepaid voucher", 40, 1),
    ("manual", "Manual adjustment", 50, 1),
    ("upi", "UPI", 60, 1),
    ("wire", "Wire transfer", 70, 1),
    ("pix", "Pix instant payment", 80, 0),
    ("card", "Credit or debit card", 90, 1),
    ("paypal", "PayPal balance", 100, 0),
    ("check", "Paper check", 110, 0),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_payment_method_labels_refresh WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # intentionally conservative: anything unexpected is left alone
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_payment_method_labels_refresh WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_payment_method_labels_refresh WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no status" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    lines = ["accounts: %d rows" % total]
    for problem in verify(conn):
        lines.append("  ! " + problem)
    if len(lines) == 1:
        lines.append("  ok")
    return lines


def upgrade(conn):
    conn.executescript(DDL)
    conn.executemany(
        "INSERT OR IGNORE INTO ref_payment_method_labels_refresh (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
