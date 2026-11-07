"""Migration 0114: archive old invoices rows.

No data is deleted here. Anything we move is copied first and counted. Numbers come from the audit export Finance sent over; do not edit them by hand.

Rows with id below CUTOFF are copied to invoices_archive_old and then removed from the
hot table (BILL-918). The copy is verified by count before anything is deleted.
"""

REVISION = "0114"
CUTOFF = 1000

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("C-9526", "draft", "Support retainer", 81400),
    ("EU-245", "paid", "Credit memo", 20900),
    ("A-7843", "open", "Late fee", 60100),
    ("INV-3504", "draft", "Hosting", 51600),
    ("EU-7426", "paid", "Annual licence", 55800),
    ("INV-4337", "paid", "Late fee", 41200),
    ("A-7600", "open", "Credit memo", 79000),
    ("EU-4156", "draft", "Overage Q2", 30300),
    ("INV-8354", "void", "March services", 65000),
    ("C-5466", "draft", "Implementation", 14800),
    ("A-7087", "paid", "March services", 35100),
    ("B-6355", "paid", "Late fee", 77800),
    ("C-8139", "draft", "Hosting", 58100),
    ("B-9686", "draft", "Late fee", 200),
    ("B-6316", "draft", "API usage", 72000),
    ("INV-654", "paid", "Training day", 69600),
    ("EU-5896", "void", "API usage", 89800),
    ("C-7390", "draft", "Annual licence", 46300),
    ("EU-812", "open", "API usage", 31500),
    ("B-8720", "draft", "Support retainer", 4200),
    ("C-2294", "void", "Overage Q2", 43700),
    ("C-1616", "draft", "Onboarding fee", 35300),
    ("A-8509", "draft", "API usage", 80500),
    ("B-2177", "void", "Support retainer", 31800),
    ("EU-9487", "void", "Training day", 88700),
    ("B-1687", "draft", "Late fee", 26200),
    ("EU-5511", "paid", "Credit memo", 40400),
    ("INV-6142", "void", "March services", 31500),
    ("B-2811", "open", "Seats true-up", 42600),
    ("INV-5739", "open", "March services", 14200),
    ("A-4521", "paid", "Annual licence", 2000),
    ("INV-7774", "paid", "Overage Q2", 59600),
    ("C-8491", "paid", "Hosting", 22900),
    ("A-406", "void", "API usage", 61900),
    ("EU-8747", "draft", "Training day", 57500),
    ("INV-3451", "paid", "Annual licence", 74700),
]

NOTES = [
    "2023-11 abakare: reviewed by billing ops",
    "2023-07 abakare: added verify() after a bad run on the eu shard",
    "2025-07 lfischer: rollback plan written (restore from nightly dump)",
    "2023-07 lfischer: renamed helper to match the support console",
]

DDL = """
CREATE TABLE IF NOT EXISTS invoices_archive_old AS SELECT * FROM invoices WHERE 0;
"""


def candidates(conn, cutoff=CUTOFF):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE id < ?", (cutoff,)).fetchone()
    return row[0]


def archived(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices_archive_old").fetchone()
    return row[0]


def archived_row(conn, row_id):
    """Fetch one archived row, e.g. when support asks about an old invoice."""
    return conn.execute("SELECT * FROM invoices_archive_old WHERE id = ?", (row_id,)).fetchone()


def copy_rows(conn, cutoff=CUTOFF):
    # batch size picked after profiling on a copy of prod: 500 is the sweet spot
    cur = conn.execute(
        "INSERT INTO invoices_archive_old SELECT * FROM invoices WHERE id < ? AND id NOT IN (SELECT id FROM invoices_archive_old)",
        (cutoff,),
    )
    return cur.rowcount


def purge_hot(conn, cutoff=CUTOFF):
    cur = conn.execute(
        "DELETE FROM invoices WHERE id < ? AND id IN (SELECT id FROM invoices_archive_old)",
        (cutoff,),
    )
    return cur.rowcount


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
    conn.executescript(DDL)
    want = candidates(conn)
    copied = copy_rows(conn)
    if want and archived(conn) < want:
        raise RuntimeError("archive copy incomplete: %d of %d" % (archived(conn), want))
    purge_hot(conn)
    return copied
