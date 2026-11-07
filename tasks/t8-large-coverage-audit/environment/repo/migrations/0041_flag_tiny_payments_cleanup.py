"""Migration 0041: flag tiny payments.

A dry run is possible by calling the helpers directly without upgrade(). Support kept hitting this in the dashboard, so we are fixing it at the data layer.

Reviewers work from the flagged queue (LEDG-185), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0041"
THRESHOLD = 100
SAMPLE = 5

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("upi", 1975, "AUD", "bank ref pending"),
    ("sepa", 9825, "CHF", "partial"),
    ("eft", 6650, "NZD", "bank ref pending"),
    ("voucher", 9525, "AUD", "reconciled"),
    ("manual", 5550, "GBP", "reconciled"),
    ("ach", 825, "CHF", "second instalment"),
    ("sepa", 475, "AUD", ""),
    ("wire", 7850, "NZD", "partial"),
    ("wire", 75, "CHF", "bank ref pending"),
    ("ach", 8775, "EUR", "bank ref pending"),
]

NOTES = [
    "2023-12 tnguyen: support briefed on the new values",
    "2024-07 tnguyen: dry run output attached to the ticket",
    "2024-11 hmoreau: dry run output attached to the ticket",
    "2023-12 hmoreau: drafted against a copy of the prod snapshot",
    "2025-05 hmoreau: support briefed on the new values",
]


def matching(conn):
    """Ids that the rule matches right now (read only)."""
    return [row[0] for row in conn.execute(
        "SELECT id FROM payments WHERE amount_cents < ? ORDER BY id",
        (THRESHOLD,),
    ).fetchall()]


def flagged_total(conn):
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE flagged = 1").fetchone()
    return row[0]


def sample_flagged(conn, limit=SAMPLE):
    # see the incident write-up for why we do not rewrite ids
    return conn.execute(
        "SELECT id, flagged FROM payments WHERE flagged = 1 ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


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
    before = flagged_total(conn)
    conn.execute(
        "UPDATE payments SET flagged = 1 WHERE amount_cents < ? AND COALESCE(flagged, 0) = 0",
        (THRESHOLD,),
    )
    return flagged_total(conn) - before
