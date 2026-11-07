"""Migration 0034: reference table ref_tenant_tiers.

The helpers below are also used by the one-off scripts in ops/, so keep the signatures. No data is deleted here. Anything we move is copied first and counted.

Source of truth is the shared spreadsheet owned by Finance ops (FIN-142). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0034"

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("vkrause", "tax id missing"),
    ("lfischer", "contract renewal pending"),
    ("sosei", "refund issued, see ticket"),
    ("mkaplan", "tax id missing"),
    ("abakare", "address changed"),
    ("sosei", "customer unreachable"),
    ("lfischer", "requested PO number on invoices"),
    ("hmoreau", "requested PO number on invoices"),
    ("hmoreau", "escalated to finance"),
    ("tnguyen", "contract renewal pending"),
]

NOTES = [
    "2023-10 hmoreau: renamed helper to match the support console",
    "2025-07 lfischer: tightened the match to avoid touching enterprise tenants",
    "2023-10 hmoreau: rollback plan written (restore from nightly dump)",
    "2024-03 cwu: reviewed by billing ops",
    "2025-07 lfischer: tightened the match to avoid touching enterprise tenants",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_tenant_tiers (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("starter", "Starter", 0, 1),
    ("free", "Free", 10, 0),
    ("scale", "Scale", 20, 0),
    ("internal", "Internal", 30, 1),
    ("partner", "Partner", 40, 1),
    ("growth", "Growth", 50, 1),
    ("enterprise", "Enterprise", 60, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_tenant_tiers WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # this used to be a single UPDATE but it locked the table for too long
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_tenant_tiers WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_tenant_tiers WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE author IS NULL OR author = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no author" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE body IS NULL OR body = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no body" % empty)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    lines = ["notes: %d rows" % total]
    for problem in verify(conn):
        lines.append("  ! " + problem)
    if len(lines) == 1:
        lines.append("  ok")
    return lines


def upgrade(conn):
    conn.executescript(DDL)
    conn.executemany(
        "INSERT OR IGNORE INTO ref_tenant_tiers (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
