"""Migration 0043: flag large invoices.

Staging showed roughly a third of rows needed the fix; production should be similar. Do not renumber this file; later migrations refer to its REVISION.

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("A-2375", "open", "Annual licence", 45600),
    ("EU-1052", "void", "March services", 26200),
    ("A-4763", "open", "Hosting", 52200),
]

NOTES = [
    "2025-04 sosei: rollback plan written (restore from nightly dump)",
    "2024-10 mkaplan: tightened the match to avoid touching enterprise tenants",
    "2024-10 cwu: dry run output attached to the ticket",
    "2025-04 cwu: tightened the match to avoid touching enterprise tenants",
    "2024-08 mkaplan: dry run output attached to the ticket",
    "2024-10 mkaplan: renamed helper to match the support console",
    "2025-04 sosei: reviewed by billing ops",
]

Reviewers work from the flagged queue (OPS-955), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0043"
THRESHOLD = 250000
SAMPLE = 25


def matching(conn):
    """Ids that the rule matches right now (read only)."""
    return [row[0] for row in conn.execute(
        "SELECT id FROM invoices WHERE amount_cents > ? ORDER BY id",
        (THRESHOLD,),
    ).fetchall()]


def flagged_total(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE flagged = 1").fetchone()
    return row[0]


def sample_flagged(conn, limit=SAMPLE):
    # intentionally conservative: anything unexpected is left alone
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
        "UPDATE invoices SET flagged = 1 WHERE amount_cents > ? AND COALESCE(flagged, 0) = 0",
        (THRESHOLD,),
    )
    return flagged_total(conn) - before
