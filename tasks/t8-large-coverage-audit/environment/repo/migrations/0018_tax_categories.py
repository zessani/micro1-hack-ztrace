"""Migration 0018: reference table ref_tax_categories.

A dry run is possible by calling the helpers directly without upgrade(). Order matters: the more specific rules run first so they are not shadowed.

Source of truth is the shared spreadsheet owned by Finance ops (BILL-780). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0018"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("finance.globex@globex.example", "Globex Billing", "apac", "suspended"),
    ("ar.bluth@bluth.example", "Bluth Health", "emea", "active"),
    ("ops.massive@massive.example", "Massive Finance", "default", "suspended"),
    ("ap.pied@pied.example", "Pied Health", "emea", "active"),
    ("ap.stark@stark.example", "Stark Finance", "na", "trial"),
    ("ops.massive@massive.example", "Massive Ops", "emea", "active"),
    ("finance.cyberdyne@cyberdyne.example", "Cyberdyne Finance", "na", "suspended"),
    ("ap.stark@stark.example", "Stark Labs", "emea", "active"),
    ("ar.wonka@wonka.example", "Wonka Media", "emea", "active"),
    ("ap.stark@stark.example", "Stark Finance", "stark", "active"),
    ("billing.acme@acme.example", "Acme Ops", "default", "suspended"),
    ("billing.soylent@soylent.example", "Soylent Media", "na", "active"),
    ("ar.soylent@soylent.example", "Soylent Labs", "soylent", "trial"),
    ("billing.globex@globex.example", "Globex Media", "apac", "suspended"),
    ("finance.soylent@soylent.example", "Soylent Finance", "default", "trial"),
    ("billing.pied@pied.example", "Pied Systems", "pied", "suspended"),
    ("finance.dunder@dunder.example", "Dunder Logistics", "na", "active"),
    ("ops.umbrella@umbrella.example", "Umbrella Retail", "default", "suspended"),
    ("ar.tyrell@tyrell.example", "Tyrell Partners", "default", "suspended"),
    ("finance.bluth@bluth.example", "Bluth Billing", "default", "trial"),
    ("finance.acme@acme.example", "Acme Media", "emea", "suspended"),
    ("ap.gringotts@gringotts.example", "Gringotts Billing", "gringotts", "active"),
    ("finance.tyrell@tyrell.example", "Tyrell Logistics", "default", "active"),
    ("finance.vandelay@vandelay.example", "Vandelay Ops", "default", "active"),
    ("ar.gringotts@gringotts.example", "Gringotts Systems", "default", "suspended"),
    ("finance.globex@globex.example", "Globex Logistics", "emea", "trial"),
    ("ap.tyrell@tyrell.example", "Tyrell Labs", "emea", "suspended"),
    ("ops.wayne@wayne.example", "Wayne Health", "emea", "trial"),
    ("billing.stark@stark.example", "Stark Partners", "default", "active"),
    ("finance.soylent@soylent.example", "Soylent Media", "apac", "suspended"),
    ("ap.cyberdyne@cyberdyne.example", "Cyberdyne Systems", "apac", "active"),
    ("ar.sterling@sterling.example", "Sterling Finance", "na", "trial"),
    ("ops.tyrell@tyrell.example", "Tyrell Media", "tyrell", "active"),
    ("ap.globex@globex.example", "Globex Media", "apac", "active"),
    ("ops.oscorp@oscorp.example", "Oscorp Logistics", "na", "active"),
    ("ap.globex@globex.example", "Globex Media", "default", "trial"),
]

NOTES = [
    "2024-03 abakare: dry run output attached to the ticket",
    "2025-08 mkaplan: rollback plan written (restore from nightly dump)",
    "2023-04 sosei: widened batch size after load test",
    "2023-12 sosei: renamed helper to match the support console",
    "2024-03 mkaplan: dry run output attached to the ticket",
    "2024-11 mkaplan: rollback plan written (restore from nightly dump)",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_tax_categories (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("hst", "HST", 0, 0),
    ("pst", "PST", 10, 1),
    ("reverse", "Reverse charge", 20, 1),
    ("oss", "EU one-stop shop", 30, 1),
    ("zero", "Zero rated", 40, 1),
    ("reduced", "Reduced rate", 50, 0),
    ("standard", "Standard rate", 60, 1),
    ("gst", "GST", 70, 1),
    ("exempt", "Exempt", 80, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_tax_categories WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # we count what we changed so the runner can log it
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_tax_categories WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_tax_categories WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE tenant IS NULL OR tenant = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no tenant" % empty)

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
        "INSERT OR IGNORE INTO ref_tax_categories (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
