"""Migration 0048: flag missing memo.

A dry run is possible by calling the helpers directly without upgrade(). Finance asked for this ahead of the quarter close; it is safe to run more than once.

Reviewers work from the flagged queue (OPS-553), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0048"
EMPTY = ""
SAMPLE = 25

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("B-3089", "void", "March services", 24400),
    ("C-1547", "open", "Onboarding fee", 29300),
    ("C-6196", "draft", "Seats true-up", 59000),
    ("A-3231", "paid", "Implementation", 85100),
    ("C-7200", "draft", "March services", 30900),
    ("B-1479", "paid", "Credit memo", 61900),
    ("INV-3836", "open", "Support retainer", 41300),
    ("B-1445", "void", "Hosting", 1600),
    ("C-7213", "paid", "API usage", 82900),
    ("B-7743", "draft", "Training day", 59500),
    ("INV-8917", "open", "Overage Q2", 86300),
    ("A-2387", "draft", "Hosting", 74300),
    ("EU-6584", "open", "March services", 26600),
    ("B-9800", "void", "Implementation", 59800),
    ("A-4715", "void", "Overage Q2", 61200),
    ("INV-6931", "open", "Seats true-up", 31900),
]

NOTES = [
    "2023-06 hmoreau: dry run output attached to the ticket",
    "2024-10 sosei: reviewed by billing ops",
    "2025-04 sosei: widened batch size after load test",
    "2023-11 sosei: rollback plan written (restore from nightly dump)",
    "2024-02 hmoreau: reviewed by billing ops",
    "2024-10 hmoreau: dry run output attached to the ticket",
    "2024-02 hmoreau: renamed helper to match the support console",
    "2025-04 hmoreau: reviewed by billing ops",
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
    # lower-case comparison, the column was never case-normalised before
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
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE memo IS NULL OR memo = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no memo" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE ref IS NULL OR ref = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no ref" % empty)
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
