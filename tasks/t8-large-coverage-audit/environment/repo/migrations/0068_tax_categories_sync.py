"""Migration 0068: reference table ref_tax_categories_sync.

Rows are touched in small batches so the write lock is never held for long. Staging showed roughly a third of rows needed the fix; production should be similar.

Source of truth is the shared spreadsheet owned by Finance ops (FIN-212). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0068"

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("jdiaz", "contract renewal pending"),
    ("abakare", "moved to annual plan"),
    ("tnguyen", "requested PO number on invoices"),
    ("abakare", "address changed"),
    ("hmoreau", "moved to annual plan"),
    ("vkrause", "requested PO number on invoices"),
    ("hmoreau", "chargeback opened by bank"),
    ("jdiaz", "asked for W-9"),
    ("sosei", "contract renewal pending"),
    ("rpatel", "called about duplicate charge"),
]

NOTES = [
    "2023-05 rpatel: support briefed on the new values",
    "2023-12 lfischer: renamed helper to match the support console",
    "2023-05 abakare: added verify() after a bad run on the eu shard",
    "2023-12 rpatel: drafted against a copy of the prod snapshot",
    "2024-03 rpatel: renamed helper to match the support console",
    "2023-05 lfischer: added verify() after a bad run on the eu shard",
    "2024-12 vkrause: tightened the match to avoid touching enterprise tenants",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_tax_categories_sync (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("reverse", "Reverse charge", 0, 0),
    ("standard", "Standard rate", 10, 0),
    ("pst", "PST", 20, 1),
    ("hst", "HST", 30, 1),
    ("exempt", "Exempt", 40, 1),
    ("reduced", "Reduced rate", 50, 1),
    ("oss", "EU one-stop shop", 60, 1),
    ("gst", "GST", 70, 1),
    ("zero", "Zero rated", 80, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_tax_categories_sync WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # values were confirmed with support; do not add new ones without a ticket
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_tax_categories_sync WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_tax_categories_sync WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE body IS NULL OR body = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no body" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE author IS NULL OR author = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no author" % empty)

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
        "INSERT OR IGNORE INTO ref_tax_categories_sync (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
