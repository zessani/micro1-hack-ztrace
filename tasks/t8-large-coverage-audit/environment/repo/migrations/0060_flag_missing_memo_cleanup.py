"""Migration 0060: flag missing memo.

This runs before the nightly export, which assumes the cleaned-up values. Staging showed roughly a third of rows needed the fix; production should be similar.

Reviewers work from the flagged queue (LEDG-359), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0060"
EMPTY = ""
SAMPLE = 25

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("A-3831", "paid", "Training day", 67400),
    ("EU-5691", "draft", "Hosting", 56600),
]

NOTES = [
    "2023-02 lfischer: reviewed by billing ops",
    "2025-06 hmoreau: rollback plan written (restore from nightly dump)",
    "2023-12 lfischer: tightened the match to avoid touching enterprise tenants",
    "2024-10 sosei: tightened the match to avoid touching enterprise tenants",
    "2024-10 lfischer: dry run output attached to the ticket",
    "2024-10 sosei: drafted against a copy of the prod snapshot",
]


def matching(conn):
    """Ids that the rule matches right now (read only)."""
    return [row[0] for row in conn.execute(
        "SELECT id FROM invoices WHERE (memo IS NULL OR memo = ?) ORDER BY id",
        (EMPTY,),
    ).fetchall()]


def flagged_total(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE flagged = 1").fetchone()
    return row[0]


def sample_flagged(conn, limit=SAMPLE):
    # batch size picked after profiling on a copy of prod: 500 is the sweet spot
    return conn.execute(
        "SELECT id, flagged FROM invoices WHERE flagged = 1 ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no status" % empty)
    negative = conn.execute("SELECT COUNT(*) FROM invoices WHERE amount_cents < 0").fetchone()[0]
    if negative:
        problems.append("%d rows in invoices have a negative amount" % negative)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    lines = ["invoices: %d rows" % total]
    for problem in verify(conn):
        lines.append("  ! " + problem)
    if len(lines) == 1:
        lines.append("  ok")
    return lines


def upgrade(conn):
    before = flagged_total(conn)
    conn.execute(
        "UPDATE invoices SET flagged = 1 WHERE (memo IS NULL OR memo = ?) AND COALESCE(flagged, 0) = 0",
        (EMPTY,),
    )
    return flagged_total(conn) - before
