"""Migration 0063: flag zero invoices.

A dry run is possible by calling the helpers directly without upgrade(). Do not renumber this file; later migrations refer to its REVISION.

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("INV-9353", "open", "Support retainer", 8400),
    ("A-8748", "draft", "March services", 20900),
    ("A-5441", "void", "Seats true-up", 24300),
    ("C-5623", "draft", "Seats true-up", 600),
    ("EU-2810", "open", "Support retainer", 81400),
    ("EU-3547", "paid", "Credit memo", 27400),
    ("EU-6693", "void", "Late fee", 76700),
    ("C-7762", "paid", "API usage", 15300),
    ("A-7570", "paid", "Annual licence", 43800),
    ("B-2370", "paid", "March services", 36100),
    ("C-593", "open", "Late fee", 89400),
    ("A-8501", "open", "Annual licence", 62800),
    ("B-5441", "void", "Seats true-up", 78700),
    ("B-854", "open", "Overage Q2", 40600),
    ("B-1686", "draft", "API usage", 52400),
    ("INV-568", "open", "API usage", 10600),
    ("C-2672", "draft", "Annual licence", 60600),
    ("A-5656", "draft", "Seats true-up", 73700),
    ("C-446", "draft", "Implementation", 26800),
    ("EU-7895", "void", "Onboarding fee", 35400),
    ("C-6244", "draft", "Annual licence", 47600),
    ("INV-9991", "void", "Seats true-up", 35200),
    ("C-302", "open", "Annual licence", 21800),
    ("B-5019", "draft", "Training day", 10800),
    ("C-7524", "void", "API usage", 52300),
    ("B-4852", "open", "Overage Q2", 47100),
    ("EU-1176", "open", "Overage Q2", 33600),
    ("A-4369", "draft", "Annual licence", 77900),
    ("A-548", "void", "Overage Q2", 47200),
    ("EU-9572", "paid", "March services", 30000),
    ("A-913", "open", "Training day", 43400),
    ("A-2878", "void", "Training day", 80200),
    ("C-7521", "paid", "Implementation", 2000),
    ("C-7189", "paid", "Seats true-up", 11200),
    ("B-6033", "void", "Training day", 46700),
    ("B-6637", "void", "Onboarding fee", 73700),
    ("B-2686", "draft", "March services", 53300),
    ("INV-5010", "draft", "Implementation", 68800),
    ("INV-9187", "paid", "Hosting", 56000),
    ("B-8150", "draft", "Implementation", 15200),
    ("EU-4458", "draft", "March services", 34700),
    ("INV-3584", "paid", "Training day", 76600),
    ("A-1301", "draft", "Annual licence", 80000),
    ("C-372", "void", "Hosting", 10300),
    ("EU-7976", "paid", "API usage", 71800),
    ("B-5731", "void", "Onboarding fee", 30400),
    ("A-6044", "void", "March services", 57400),
    ("A-729", "paid", "Late fee", 22600),
    ("B-6611", "paid", "Seats true-up", 10700),
    ("A-3715", "draft", "Late fee", 74200),
]

NOTES = [
    "2024-12 cwu: rehearsed on staging, 2708 rows touched",
    "2024-07 lfischer: rehearsed on staging, 2708 rows touched",
    "2023-02 tnguyen: rollback plan written (restore from nightly dump)",
    "2023-10 cwu: added verify() after a bad run on the eu shard",
    "2025-06 abakare: support briefed on the new values",
    "2023-10 abakare: renamed helper to match the support console",
    "2023-02 lfischer: dry run output attached to the ticket",
    "2024-07 abakare: support briefed on the new values",
]

Reviewers work from the flagged queue (SUP-211), so we only ever set flagged to 1
here; clearing is a manual action in the admin UI.
"""

REVISION = "0063"
IGNORED_STATUS = "void"
SAMPLE = 5


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
    # keep this in sync with the export job's expectations
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
        "UPDATE invoices SET flagged = 1 WHERE amount_cents = 0 AND status != ? AND COALESCE(flagged, 0) = 0",
        (IGNORED_STATUS,),
    )
    return flagged_total(conn) - before
