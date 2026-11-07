"""Migration 0075: flag zero invoices.

No data is deleted here. Anything we move is copied first and counted. The change is idempotent: rerunning on an already migrated database is a no-op.

Reviewers work from the flagged queue (LEDG-495), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0075"
IGNORED_STATUS = "void"
SAMPLE = 5

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("A-1143", "void", "Implementation", 74500),
    ("A-4067", "void", "API usage", 77900),
    ("A-1022", "void", "Support retainer", 79000),
    ("INV-3839", "draft", "Support retainer", 39400),
    ("C-5414", "open", "Credit memo", 50600),
    ("B-7145", "open", "Implementation", 9100),
    ("EU-5734", "draft", "Overage Q2", 58700),
    ("EU-2992", "paid", "API usage", 43500),
]

NOTES = [
    "2024-01 sosei: renamed helper to match the support console",
    "2024-01 lfischer: reviewed by billing ops",
    "2023-11 sosei: support briefed on the new values",
    "2023-05 mkaplan: widened batch size after load test",
    "2025-07 mkaplan: support briefed on the new values",
]


def matching(conn):
    """Ids that the rule matches right now (read only)."""
    return [row[0] for row in conn.execute(
        "SELECT id FROM invoices WHERE amount_cents = 0 AND status != ? ORDER BY id",
        (IGNORED_STATUS,),
    ).fetchall()]


def flagged_total(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE flagged = 1").fetchone()
    return row[0]


def sample_flagged(conn, limit=SAMPLE):
    # SQLite has no ALTER ... IF NOT EXISTS, so we look at table_info first
    return conn.execute(
        "SELECT id, flagged FROM invoices WHERE flagged = 1 ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE ref IS NULL OR ref = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no ref" % empty)
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
        "UPDATE invoices SET flagged = 1 WHERE amount_cents = 0 AND status != ? AND COALESCE(flagged, 0) = 0",
        (IGNORED_STATUS,),
    )
    return flagged_total(conn) - before
