"""Migration 0095: reference table ref_tax_categories_additions.

Rows are touched in small batches so the write lock is never held for long. The old behaviour is kept behind the same helper names so callers do not change.

Source of truth is the shared spreadsheet owned by Finance ops (SUP-783). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0095"

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("upi", 1875, "NZD", "reconciled"),
    ("manual", 7675, "AUD", "bank ref pending"),
    ("pix", 300, "SEK", ""),
    ("eft", 6250, "CAD", ""),
    ("eft", 5525, "CHF", "partial"),
    ("manual", 4100, "EUR", "bank ref pending"),
    ("wire", 9400, "CHF", "reconciled"),
    ("ach", 7125, "NZD", "reconciled"),
    ("upi", 8875, "SEK", "reconciled"),
    ("bacs", 8975, "SEK", "bank ref pending"),
    ("ach", 675, "NZD", "reconciled"),
    ("pix", 5875, "SEK", "second instalment"),
    ("pix", 5475, "EUR", "reconciled"),
    ("paypal", 6675, "AUD", "bank ref pending"),
    ("bacs", 3325, "SEK", "partial"),
    ("wire", 9250, "CHF", "reconciled"),
]

NOTES = [
    "2025-07 rpatel: tightened the match to avoid touching enterprise tenants",
    "2023-11 hmoreau: dry run output attached to the ticket",
    "2023-11 rpatel: rollback plan written (restore from nightly dump)",
    "2024-12 mkaplan: dry run output attached to the ticket",
    "2025-07 hmoreau: widened batch size after load test",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_tax_categories_additions (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("reverse", "Reverse charge", 0, 0),
    ("oss", "EU one-stop shop", 10, 0),
    ("hst", "HST", 20, 1),
    ("gst", "GST", 30, 1),
    ("zero", "Zero rated", 40, 1),
    ("pst", "PST", 50, 0),
    ("exempt", "Exempt", 60, 1),
    ("reduced", "Reduced rate", 70, 1),
    ("standard", "Standard rate", 80, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_tax_categories_additions WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # keep this in sync with the export job's expectations
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_tax_categories_additions WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_tax_categories_additions WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE note IS NULL OR note = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no note" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE currency IS NULL OR currency = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no currency" % empty)
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
        "INSERT OR IGNORE INTO ref_tax_categories_additions (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
