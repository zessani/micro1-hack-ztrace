"""Migration 0064: flag refunds.

Do not renumber this file; later migrations refer to its REVISION. No data is deleted here. Anything we move is copied first and counted.

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("eft", 4425, "EUR", "bank ref pending"),
    ("card", 5700, "SEK", "bank ref pending"),
    ("cash", 4000, "AUD", "reconciled"),
    ("credit", 5725, "NZD", "partial"),
    ("cash", 2425, "CHF", "reconciled"),
    ("check", 1200, "CHF", "second instalment"),
    ("interac", 2575, "AUD", "second instalment"),
    ("voucher", 6025, "GBP", "partial"),
    ("interac", 9975, "CAD", "bank ref pending"),
    ("sepa", 7250, "NZD", "bank ref pending"),
    ("voucher", 6825, "CHF", "second instalment"),
    ("upi", 8250, "GBP", "bank ref pending"),
    ("interac", 9500, "USD", ""),
    ("card", 7700, "GBP", "reconciled"),
    ("voucher", 2025, "NZD", ""),
    ("paypal", 6300, "NZD", "second instalment"),
    ("ach", 5450, "AUD", "reconciled"),
    ("bacs", 2025, "GBP", "reconciled"),
    ("manual", 8200, "SEK", "second instalment"),
    ("upi", 3700, "CHF", "partial"),
    ("voucher", 4850, "AUD", "second instalment"),
    ("cash", 9450, "AUD", "second instalment"),
    ("card", 4625, "EUR", "partial"),
    ("card", 9975, "SEK", "reconciled"),
    ("wire", 2925, "CAD", "second instalment"),
    ("credit", 3000, "AUD", ""),
    ("upi", 1500, "GBP", "second instalment"),
    ("paypal", 6975, "USD", "second instalment"),
    ("cash", 2850, "CHF", "reconciled"),
    ("bacs", 1350, "USD", "second instalment"),
    ("check", 3050, "CHF", "second instalment"),
    ("pix", 5200, "GBP", "bank ref pending"),
    ("check", 3300, "EUR", ""),
    ("credit", 7950, "NZD", "partial"),
    ("upi", 7800, "CAD", "reconciled"),
    ("credit", 4075, "CAD", "partial"),
    ("upi", 8625, "CAD", "reconciled"),
    ("interac", 2275, "GBP", ""),
    ("voucher", 2725, "USD", "bank ref pending"),
    ("check", 2375, "SEK", ""),
    ("voucher", 9775, "GBP", "partial"),
    ("manual", 9600, "GBP", "second instalment"),
    ("paypal", 3375, "AUD", "partial"),
    ("credit", 7800, "SEK", "partial"),
    ("voucher", 3125, "GBP", "reconciled"),
    ("wire", 8400, "USD", "reconciled"),
    ("voucher", 575, "CHF", ""),
    ("bacs", 3750, "AUD", "bank ref pending"),
    ("check", 5175, "EUR", "reconciled"),
    ("pix", 3025, "CHF", "partial"),
]

NOTES = [
    "2023-09 hmoreau: reviewed by billing ops",
    "2023-10 tnguyen: rehearsed on staging, 2034 rows touched",
    "2024-08 cwu: rollback plan written (restore from nightly dump)",
    "2024-08 hmoreau: dry run output attached to the ticket",
    "2023-09 hmoreau: reviewed by billing ops",
    "2024-11 cwu: support briefed on the new values",
    "2024-11 tnguyen: rehearsed on staging, 2034 rows touched",
    "2024-11 hmoreau: renamed helper to match the support console",
]

Reviewers work from the flagged queue (LEDG-284), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0064"
REFUND_FLAG = 1
SAMPLE = 10


def matching(conn):
    """Ids that the rule matches right now (read only)."""
    return [row[0] for row in conn.execute(
        "SELECT id FROM payments WHERE COALESCE(refund, 0) = ? ORDER BY id",
        (REFUND_FLAG,),
    ).fetchall()]


def flagged_total(conn):
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE flagged = 1").fetchone()
    return row[0]


def sample_flagged(conn, limit=SAMPLE):
    # TODO(billing): drop once the legacy importer is gone
    return conn.execute(
        "SELECT id, flagged FROM payments WHERE flagged = 1 ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def notes_by_author(conn, author):
    """Support console: every note written by one agent."""
    return conn.execute("SELECT id, account_id, author FROM notes WHERE author = '{}' ORDER BY id".format(author)).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE method IS NULL OR method = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no method" % empty)
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
    before = flagged_total(conn)
    conn.execute(
        "UPDATE payments SET flagged = 1 WHERE COALESCE(refund, 0) = ? AND COALESCE(flagged, 0) = 0",
        (REFUND_FLAG,),
    )
    return flagged_total(conn) - before
