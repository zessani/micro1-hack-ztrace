"""Migration 0029: reference table ref_dunning_stages.

A dry run is possible by calling the helpers directly without upgrade(). Do not renumber this file; later migrations refer to its REVISION.

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("voucher", 675, "CAD", ""),
    ("eft", 6600, "NZD", "bank ref pending"),
]

NOTES = [
    "2023-12 cwu: tightened the match to avoid touching enterprise tenants",
    "2024-11 rpatel: support briefed on the new values",
    "2024-07 rpatel: renamed helper to match the support console",
    "2024-11 tnguyen: widened batch size after load test",
    "2023-12 rpatel: rehearsed on staging, 3839 rows touched",
    "2024-07 tnguyen: support briefed on the new values",
    "2024-11 rpatel: rehearsed on staging, 3839 rows touched",
    "2025-04 tnguyen: support briefed on the new values",
    "2023-04 rpatel: rollback plan written (restore from nightly dump)",
]

Source of truth is the shared spreadsheet owned by Finance ops (FIN-679). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0029"

DDL = """
CREATE TABLE IF NOT EXISTS ref_dunning_stages (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("d21", "Suspension warning", 0, 1),
    ("d30", "Suspended", 10, 1),
    ("d0", "Invoice sent", 20, 1),
    ("d45", "Sent to collections", 30, 1),
    ("d60", "Written off", 40, 1),
    ("d14", "Final notice", 50, 1),
    ("d7", "Second reminder", 60, 1),
    ("d3", "Friendly reminder", 70, 0),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_dunning_stages WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # NULL and empty string are both treated as 'missing' on purpose
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_dunning_stages WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_dunning_stages WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE note IS NULL OR note = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no note" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE method IS NULL OR method = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no method" % empty)
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
        "INSERT OR IGNORE INTO ref_dunning_stages (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
