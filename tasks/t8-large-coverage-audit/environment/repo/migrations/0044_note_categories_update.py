"""Migration 0044: reference table ref_note_categories_update.

Rows are touched in small batches so the write lock is never held for long. Numbers come from the audit export Finance sent over; do not edit them by hand.

Source of truth is the shared spreadsheet owned by Finance ops (FIN-695). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0044"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("billing.bluth@bluth.example", "Bluth Ops", "emea", "suspended"),
    ("ar.soylent@soylent.example", "Soylent Retail", "na", "suspended"),
]

NOTES = [
    "2023-08 rpatel: added verify() after a bad run on the eu shard",
    "2023-10 abakare: rollback plan written (restore from nightly dump)",
    "2024-09 rpatel: reviewed by billing ops",
    "2023-10 abakare: widened batch size after load test",
    "2023-10 sosei: renamed helper to match the support console",
    "2024-12 abakare: dry run output attached to the ticket",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_note_categories_update (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("downgrade", "Plan downgrade", 0, 1),
    ("tax", "Tax or VAT", 10, 1),
    ("refund", "Refund request", 20, 1),
    ("goodwill", "Goodwill credit", 30, 1),
    ("upgrade", "Plan upgrade", 40, 1),
    ("legal", "Legal hold", 50, 1),
    ("dunning", "Dunning follow-up", 60, 0),
    ("onboarding", "Onboarding", 70, 1),
    ("dispute", "Payment dispute", 80, 0),
    ("fraud", "Fraud review", 90, 0),
    ("kyc", "Identity verification", 100, 0),
    ("cancel", "Cancellation", 110, 1),
    ("billing", "Billing question", 120, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_note_categories_update WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # SQLite has no ALTER ... IF NOT EXISTS, so we look at table_info first
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_note_categories_update WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_note_categories_update WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no status" % empty)

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
        "INSERT OR IGNORE INTO ref_note_categories_update (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
