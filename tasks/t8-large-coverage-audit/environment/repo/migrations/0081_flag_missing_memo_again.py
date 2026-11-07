"""Migration 0081: flag missing memo.

Order matters: the more specific rules run first so they are not shadowed. The change is idempotent: rerunning on an already migrated database is a no-op.

Reviewers work from the flagged queue (FIN-108), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0081"
EMPTY = ""
SAMPLE = 5

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("C-4644", "draft", "Training day", 51200),
    ("B-3693", "paid", "Training day", 32700),
    ("INV-6810", "open", "Credit memo", 82700),
    ("EU-7060", "void", "March services", 33100),
    ("B-8472", "void", "Seats true-up", 23800),
    ("A-8151", "open", "Seats true-up", 1800),
    ("B-9356", "open", "Hosting", 31900),
    ("EU-4599", "void", "March services", 74100),
    ("EU-6559", "paid", "Late fee", 76700),
    ("EU-7581", "open", "Late fee", 23200),
    ("A-6338", "void", "Annual licence", 88400),
    ("A-9699", "open", "Seats true-up", 13000),
    ("EU-8938", "draft", "Support retainer", 12400),
    ("INV-217", "open", "March services", 15700),
    ("B-8832", "open", "API usage", 35700),
    ("A-5854", "open", "March services", 72400),
]

NOTES = [
    "2023-12 mkaplan: added verify() after a bad run on the eu shard",
    "2024-11 lfischer: reviewed by billing ops",
    "2024-11 lfischer: widened batch size after load test",
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
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE memo IS NULL OR memo = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no memo" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no status" % empty)
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
