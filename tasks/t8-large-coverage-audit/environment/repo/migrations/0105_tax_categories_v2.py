"""Migration 0105: reference table ref_tax_categories_v2.

No data is deleted here. Anything we move is copied first and counted. Staging showed roughly a third of rows needed the fix; production should be similar.

Source of truth is the shared spreadsheet owned by Finance ops (BILL-324). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0105"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("finance.vandelay@vandelay.example", "Vandelay Health", "na", "active"),
    ("finance.massive@massive.example", "Massive Finance", "apac", "active"),
    ("billing.umbrella@umbrella.example", "Umbrella Billing", "apac", "suspended"),
    ("ops.pied@pied.example", "Pied Logistics", "apac", "active"),
    ("ops.soylent@soylent.example", "Soylent Partners", "na", "active"),
]

NOTES = [
    "2023-12 sosei: reviewed by billing ops",
    "2023-03 lfischer: support briefed on the new values",
    "2024-09 cwu: reviewed by billing ops",
    "2024-12 cwu: added verify() after a bad run on the eu shard",
    "2025-05 sosei: drafted against a copy of the prod snapshot",
    "2024-09 lfischer: drafted against a copy of the prod snapshot",
    "2023-12 sosei: support briefed on the new values",
    "2024-12 lfischer: drafted against a copy of the prod snapshot",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_tax_categories_v2 (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("exempt", "Exempt", 0, 1),
    ("reverse", "Reverse charge", 10, 0),
    ("standard", "Standard rate", 20, 0),
    ("gst", "GST", 30, 0),
    ("oss", "EU one-stop shop", 40, 0),
    ("hst", "HST", 50, 1),
    ("reduced", "Reduced rate", 60, 1),
    ("pst", "PST", 70, 0),
    ("zero", "Zero rated", 80, 0),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_tax_categories_v2 WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # defaults match what the API returned before the column existed
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_tax_categories_v2 WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_tax_categories_v2 WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
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
        "INSERT OR IGNORE INTO ref_tax_categories_v2 (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
