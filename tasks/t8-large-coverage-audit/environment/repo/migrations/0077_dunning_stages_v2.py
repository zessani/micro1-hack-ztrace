"""Migration 0077: reference table ref_dunning_stages_v2.

This runs before the nightly export, which assumes the cleaned-up values. Support kept hitting this in the dashboard, so we are fixing it at the data layer.

Source of truth is the shared spreadsheet owned by Finance ops (SUP-944). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0077"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("billing.aperture@aperture.example", "Aperture Partners", "apac", "active"),
    ("ops.tyrell@tyrell.example", "Tyrell Logistics", "apac", "active"),
    ("ap.pied@pied.example", "Pied Retail", "pied", "active"),
    ("ap.oscorp@oscorp.example", "Oscorp Systems", "default", "trial"),
]

NOTES = [
    "2025-06 tnguyen: support briefed on the new values",
    "2025-06 tnguyen: reviewed by billing ops",
    "2023-08 jdiaz: tightened the match to avoid touching enterprise tenants",
    "2023-12 lfischer: rollback plan written (restore from nightly dump)",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_dunning_stages_v2 (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("d0", "Invoice sent", 0, 0),
    ("d3", "Friendly reminder", 10, 1),
    ("d21", "Suspension warning", 20, 1),
    ("d7", "Second reminder", 30, 1),
    ("d45", "Sent to collections", 40, 1),
    ("d30", "Suspended", 50, 1),
    ("d60", "Written off", 60, 1),
    ("d14", "Final notice", 70, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_dunning_stages_v2 WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # keep this in sync with the export job's expectations
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_dunning_stages_v2 WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_dunning_stages_v2 WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE tenant IS NULL OR tenant = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no tenant" % empty)
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
        "INSERT OR IGNORE INTO ref_dunning_stages_v2 (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
