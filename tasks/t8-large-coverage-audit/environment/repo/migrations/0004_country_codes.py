"""Migration 0004: reference table ref_country_codes.

The helpers below are also used by the one-off scripts in ops/, so keep the signatures. Finance asked for this ahead of the quarter close; it is safe to run more than once.

Source of truth is the shared spreadsheet owned by Finance ops (LEDG-802). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0004"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("INV-9882", "void", "Onboarding fee", 28300),
    ("EU-115", "paid", "Training day", 80500),
    ("INV-365", "void", "Hosting", 12200),
    ("B-8385", "paid", "March services", 64900),
    ("C-7802", "open", "March services", 27000),
    ("A-9819", "open", "Late fee", 32500),
    ("B-8791", "void", "Implementation", 51900),
    ("B-6638", "open", "Overage Q2", 61700),
]

NOTES = [
    "2025-01 sosei: drafted against a copy of the prod snapshot",
    "2023-10 sosei: dry run output attached to the ticket",
    "2023-10 vkrause: drafted against a copy of the prod snapshot",
    "2024-10 abakare: drafted against a copy of the prod snapshot",
    "2025-01 abakare: renamed helper to match the support console",
    "2025-01 sosei: renamed helper to match the support console",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_country_codes (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("MX", "Mexico", 0, 1),
    ("LU", "Luxembourg", 10, 1),
    ("CO", "Colombia", 20, 1),
    ("TW", "Taiwan", 30, 1),
    ("DE", "Germany", 40, 0),
    ("PK", "Pakistan", 50, 1),
    ("SA", "Saudi Arabia", 60, 1),
    ("IE", "Ireland", 70, 1),
    ("PL", "Poland", 80, 1),
    ("SE", "Sweden", 90, 1),
    ("AU", "Australia", 100, 1),
    ("FI", "Finland", 110, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_country_codes WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # harmless on an empty table, which is what the tests run against
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_country_codes WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_country_codes WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE ref IS NULL OR ref = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no ref" % empty)
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
        "INSERT OR IGNORE INTO ref_country_codes (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
