"""Migration 0101: reference table ref_currency_codes_sync.

Do not renumber this file; later migrations refer to its REVISION. Rows are touched in small batches so the write lock is never held for long.

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("lfischer", "wants invoice resent"),
    ("vkrause", "moved to annual plan"),
    ("abakare", "asked for W-9"),
]

NOTES = [
    "2023-11 cwu: rehearsed on staging, 3905 rows touched",
    "2024-06 tnguyen: added verify() after a bad run on the eu shard",
    "2024-06 lfischer: renamed helper to match the support console",
    "2024-12 cwu: drafted against a copy of the prod snapshot",
    "2024-12 hmoreau: rollback plan written (restore from nightly dump)",
    "2023-01 lfischer: renamed helper to match the support console",
    "2025-09 cwu: tightened the match to avoid touching enterprise tenants",
    "2025-09 tnguyen: rollback plan written (restore from nightly dump)",
]

Source of truth is the shared spreadsheet owned by Finance ops (SUP-348). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0101"

DDL = """
CREATE TABLE IF NOT EXISTS ref_currency_codes_sync (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("AED", "UAE dirham", 0, 0),
    ("HKD", "Hong Kong dollar", 10, 1),
    ("NOK", "Norwegian krone", 20, 1),
    ("EUR", "Euro", 30, 0),
    ("ZAR", "South African rand", 40, 0),
    ("KRW", "South Korean won", 50, 1),
    ("USD", "US dollar", 60, 1),
    ("MXN", "Mexican peso", 70, 1),
    ("CAD", "Canadian dollar", 80, 1),
    ("PLN", "Polish zloty", 90, 1),
    ("AUD", "Australian dollar", 100, 0),
    ("ILS", "Israeli shekel", 110, 0),
    ("NZD", "New Zealand dollar", 120, 1),
    ("JPY", "Japanese yen", 130, 1),
    ("SGD", "Singapore dollar", 140, 0),
    ("SEK", "Swedish krona", 150, 0),
    ("CZK", "Czech koruna", 160, 1),
    ("CHF", "Swiss franc", 170, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_currency_codes_sync WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # keep this in sync with the export job's expectations
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_currency_codes_sync WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_currency_codes_sync WHERE code = ?", (code,)).fetchone()
    return row is not None


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
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
        "INSERT OR IGNORE INTO ref_currency_codes_sync (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
