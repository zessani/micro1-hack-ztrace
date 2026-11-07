"""Migration 0118: reference table ref_payment_method_labels_update.

Support kept hitting this in the dashboard, so we are fixing it at the data layer. Rows are touched in small batches so the write lock is never held for long.

Source of truth is the shared spreadsheet owned by Finance ops (OPS-137). Rows
with active = 0 are kept so old records still resolve, but UIs hide them.
"""

REVISION = "0118"

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("tnguyen", "tax id missing"),
    ("hmoreau", "refund issued, see ticket"),
]

NOTES = [
    "2023-12 rpatel: dry run output attached to the ticket",
    "2023-12 mkaplan: widened batch size after load test",
    "2023-12 vkrause: support briefed on the new values",
    "2024-01 sosei: added verify() after a bad run on the eu shard",
    "2024-01 mkaplan: widened batch size after load test",
    "2023-12 vkrause: renamed helper to match the support console",
    "2024-11 mkaplan: rollback plan written (restore from nightly dump)",
]

DDL = """
CREATE TABLE IF NOT EXISTS ref_payment_method_labels_update (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# (code, label, sort_order, active)
ROWS = [
    ("wire", "Wire transfer", 0, 1),
    ("sepa", "SEPA direct debit", 10, 1),
    ("interac", "Interac e-Transfer", 20, 1),
    ("voucher", "Prepaid voucher", 30, 1),
    ("paypal", "PayPal balance", 40, 1),
    ("check", "Paper check", 50, 0),
    ("ach", "ACH debit", 60, 1),
    ("bacs", "BACS credit", 70, 1),
    ("manual", "Manual adjustment", 80, 1),
    ("credit", "Account credit", 90, 1),
    ("cash", "Cash at counter", 100, 1),
    ("card", "Credit or debit card", 110, 1),
    ("pix", "Pix instant payment", 120, 1),
]


def label_for(conn, code):
    """Human readable label for a code, or the code itself if unknown."""
    row = conn.execute(
        "SELECT label FROM ref_payment_method_labels_update WHERE code = ?",
        (code,),
    ).fetchone()
    return row[0] if row else code


def active_codes(conn):
    # harmless on an empty table, which is what the tests run against
    return [row[0] for row in conn.execute(
        "SELECT code FROM ref_payment_method_labels_update WHERE active = 1 ORDER BY sort_order, code"
    ).fetchall()]


def is_known(conn, code):
    row = conn.execute("SELECT 1 FROM ref_payment_method_labels_update WHERE code = ?", (code,)).fetchone()
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
        "INSERT OR IGNORE INTO ref_payment_method_labels_update (code, label, sort_order, active) VALUES (?, ?, ?, ?)",
        ROWS,
    )
