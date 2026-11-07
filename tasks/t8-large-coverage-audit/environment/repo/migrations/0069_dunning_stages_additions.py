"""Migration 0069: reference table ref_dunning_stages_additions.

Do not renumber this file; later migrations refer to its REVISION. Rows are touched in small batches so the write lock is never held for long.

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("credit", 8725, "NZD", "partial"),
    ("voucher", 5925, "AUD", "second instalment"),
    ("eft", 5550, "SEK", "partial"),
    ("manual", 9200, "AUD", "bank ref pending"),
    ("card", 5550, "NZD", "bank ref pending"),
    ("eft", 6275, "SEK", "bank ref pending"),
    ("check", 5750, "GBP", "partial"),
    ("paypal", 2700, "SEK", "reconciled"),
    ("eft", 5175, "CAD", "bank ref pending"),
    ("credit", 7775, "AUD", "partial"),
    ("eft", 5100, "CAD", ""),
    ("credit", 1525, "CHF", "reconciled"),
    ("check", 6250, "CAD", "partial"),
    ("sepa", 8925, "AUD", "second instalment"),
    ("wire", 9550, "USD", "bank ref pending"),
    ("eft", 1600, "SEK", "partial"),
]

NOTES = [
    "2024-07 cwu: reviewed by billing ops",
    "2024-12 hmoreau: widened batch size after load test",
    "2025-05 cwu: dry run output attached to the ticket",
    "2024-12 hmoreau: rehearsed on staging, 5214 rows touched",
]

Source of truth is the shared spreadsheet owned by Finance ops (LEDG-195). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0069"

DDL = """
CREATE TABLE IF NOT EXISTS ref_dunning_stages_additions (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("d45", "Sent to collections", 0, 1),
    ("d60", "Written off", 10, 1),
    ("d7", "Second reminder", 20, 1),
    ("d14", "Final notice", 30, 1),
    ("d0", "Invoice sent", 40, 1),
    ("d30", "Suspended", 50, 1),
    ("d21", "Suspension warning", 60, 1),
    ("d3", "Friendly reminder", 70, 0),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_dunning_stages_additions WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # batch size picked after profiling on a copy of prod: 500 is the sweet spot
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_dunning_stages_additions WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_dunning_stages_additions WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE method IS NULL OR method = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no method" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE note IS NULL OR note = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no note" % empty)
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
        "INSERT OR IGNORE INTO ref_dunning_stages_additions (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
