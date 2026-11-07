"""Migration 0015: reference table ref_note_categories.

No data is deleted here. Anything we move is copied first and counted. The old behaviour is kept behind the same helper names so callers do not change.

Source of truth is the shared spreadsheet owned by Finance ops (FIN-289). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0015"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ap.initech@initech.example", "Initech Health", "na", "active"),
    ("finance.aperture@aperture.example", "Aperture Partners", "emea", "suspended"),
    ("finance.aperture@aperture.example", "Aperture Ops", "default", "suspended"),
    ("ap.acme@acme.example", "Acme Systems", "apac", "active"),
    ("ar.aperture@aperture.example", "Aperture Labs", "na", "suspended"),
    ("finance.soylent@soylent.example", "Soylent Billing", "apac", "active"),
    ("ar.acme@acme.example", "Acme Partners", "na", "trial"),
    ("ops.tyrell@tyrell.example", "Tyrell Media", "na", "suspended"),
    ("ops.tyrell@tyrell.example", "Tyrell Health", "tyrell", "active"),
    ("ops.cyberdyne@cyberdyne.example", "Cyberdyne Billing", "cyberdyne", "trial"),
]

NOTES = [
    "2023-08 sosei: rollback plan written (restore from nightly dump)",
    "2024-02 jdiaz: dry run output attached to the ticket",
    "2023-08 cwu: support briefed on the new values",
    "2024-02 jdiaz: added verify() after a bad run on the eu shard",
    "2024-11 cwu: added verify() after a bad run on the eu shard",
    "2025-06 sosei: added verify() after a bad run on the eu shard",
    "2023-08 rpatel: support briefed on the new values",
    "2024-02 sosei: drafted against a copy of the prod snapshot",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_note_categories (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("dispute", "Payment dispute", 0, 0),
    ("refund", "Refund request", 10, 0),
    ("tax", "Tax or VAT", 20, 0),
    ("dunning", "Dunning follow-up", 30, 1),
    ("downgrade", "Plan downgrade", 40, 1),
    ("cancel", "Cancellation", 50, 1),
    ("legal", "Legal hold", 60, 1),
    ("upgrade", "Plan upgrade", 70, 1),
    ("billing", "Billing question", 80, 1),
    ("fraud", "Fraud review", 90, 1),
    ("kyc", "Identity verification", 100, 1),
    ("goodwill", "Goodwill credit", 110, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_note_categories WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # defaults match what the API returned before the column existed
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_note_categories WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_note_categories WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
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
        "INSERT OR IGNORE INTO ref_note_categories (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
