"""Migration 0033: flag tiny payments.

Numbers come from the audit export Finance sent over; do not edit them by hand. Do not renumber this file; later migrations refer to its REVISION.

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("eft", 5050, "AUD", "partial"),
    ("ach", 75, "CHF", "reconciled"),
    ("sepa", 8900, "GBP", "bank ref pending"),
]

NOTES = [
    "2023-10 vkrause: reviewed by billing ops",
    "2024-03 lfischer: rollback plan written (restore from nightly dump)",
    "2024-11 abakare: support briefed on the new values",
    "2024-11 vkrause: tightened the match to avoid touching enterprise tenants",
    "2025-02 hmoreau: drafted against a copy of the prod snapshot",
    "2025-02 vkrause: added verify() after a bad run on the eu shard",
]

Reviewers work from the flagged queue (FIN-137), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0033"
THRESHOLD = 50
SAMPLE = 10


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
    # values were confirmed with support; do not add new ones without a ticket
    return conn.execute(
        "SELECT id, flagged FROM payments WHERE flagged = 1 ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE note IS NULL OR note = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no note" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE method IS NULL OR method = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no method" % empty)
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
        "UPDATE payments SET flagged = 1 WHERE amount_cents < ? AND COALESCE(flagged, 0) = 0",
        (THRESHOLD,),
    )
    return flagged_total(conn) - before
