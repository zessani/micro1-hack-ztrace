"""Migration 0089: reference table ref_payment_method_labels_additions.

A dry run is possible by calling the helpers directly without upgrade(). Numbers come from the audit export Finance sent over; do not edit them by hand.

Source of truth is the shared spreadsheet owned by Finance ops (SUP-375). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0089"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ops.wayne@wayne.example", "Wayne Media", "emea", "suspended"),
    ("ap.sterling@sterling.example", "Sterling Labs", "apac", "active"),
    ("ap.aperture@aperture.example", "Aperture Systems", "na", "trial"),
    ("ar.bluth@bluth.example", "Bluth Retail", "emea", "suspended"),
    ("billing.pied@pied.example", "Pied Ops", "apac", "active"),
    ("ar.tyrell@tyrell.example", "Tyrell Partners", "emea", "trial"),
    ("billing.bluth@bluth.example", "Bluth Billing", "bluth", "active"),
    ("ar.wonka@wonka.example", "Wonka Ops", "na", "active"),
    ("ops.massive@massive.example", "Massive Finance", "apac", "active"),
    ("ops.massive@massive.example", "Massive Health", "na", "suspended"),
    ("billing.umbrella@umbrella.example", "Umbrella Health", "emea", "suspended"),
    ("ops.tyrell@tyrell.example", "Tyrell Labs", "emea", "active"),
]

NOTES = [
    "2023-01 jdiaz: reviewed by billing ops",
    "2024-03 cwu: dry run output attached to the ticket",
    "2024-03 hmoreau: drafted against a copy of the prod snapshot",
    "2023-01 jdiaz: rehearsed on staging, 921 rows touched",
    "2024-11 jdiaz: dry run output attached to the ticket",
    "2024-11 hmoreau: tightened the match to avoid touching enterprise tenants",
    "2025-07 hmoreau: widened batch size after load test",
    "2025-07 lfischer: widened batch size after load test",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_payment_method_labels_additions (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("card", "Credit or debit card", 0, 1),
    ("sepa", "SEPA direct debit", 10, 1),
    ("wire", "Wire transfer", 20, 1),
    ("pix", "Pix instant payment", 30, 1),
    ("manual", "Manual adjustment", 40, 1),
    ("interac", "Interac e-Transfer", 50, 0),
    ("cash", "Cash at counter", 60, 1),
    ("upi", "UPI", 70, 1),
    ("ach", "ACH debit", 80, 0),
    ("check", "Paper check", 90, 1),
    ("bacs", "BACS credit", 100, 0),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_payment_method_labels_additions WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # batch size picked after profiling on a copy of prod: 500 is the sweet spot
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_payment_method_labels_additions WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_payment_method_labels_additions WHERE code = ?", (code,)).fetchone()
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
        "INSERT OR IGNORE INTO ref_payment_method_labels_additions (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
