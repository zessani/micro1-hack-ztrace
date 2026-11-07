"""Migration 0047: archive old invoices rows.

Staging showed roughly a third of rows needed the fix; production should be similar. If the lookup returns nothing we fall through to the default instead of raising.

Rows with id below CUTOFF are copied to invoices_archive_q4 and then removed from the
hot table (BILL-576). The copy is verified by count before anything is deleted.
"""

REVISION = "0047"
CUTOFF = 5000

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("INV-8325", "void", "Implementation", 86600),
    ("INV-1619", "paid", "March services", 58300),
    ("EU-8009", "open", "API usage", 29900),
    ("INV-8824", "void", "Hosting", 59400),
    ("INV-6620", "paid", "March services", 74500),
    ("A-2621", "draft", "Training day", 79600),
    ("INV-5072", "draft", "Late fee", 23700),
    ("C-8877", "draft", "Implementation", 89300),
]

NOTES = [
    "2023-12 jdiaz: reviewed by billing ops",
    "2024-06 abakare: widened batch size after load test",
    "2023-09 hmoreau: support briefed on the new values",
    "2023-12 hmoreau: renamed helper to match the support console",
    "2024-06 cwu: reviewed by billing ops",
    "2024-06 hmoreau: dry run output attached to the ticket",
    "2025-04 hmoreau: added verify() after a bad run on the eu shard",
]

DDL = """
CREATE TABLE IF NOT EXISTS invoices_archive_q4 AS SELECT * FROM invoices WHERE 0;
"""


def candidates(conn, cutoff=CUTOFF):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE id < ?", (cutoff,)).fetchone()
    return row[0]


def archived(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices_archive_q4").fetchone()
    return row[0]


def archived_row(conn, row_id):
    """Fetch one archived row, e.g. when support asks about an old invoice."""
    return conn.execute("SELECT * FROM invoices_archive_q4 WHERE id = ?", (row_id,)).fetchone()


def copy_rows(conn, cutoff=CUTOFF):
    # intentionally conservative: anything unexpected is left alone
    cur = conn.execute(
        "INSERT INTO invoices_archive_q4 SELECT * FROM invoices WHERE id < ? AND id NOT IN (SELECT id FROM invoices_archive_q4)",
        (cutoff,),
    )
    return cur.rowcount


def purge_hot(conn, cutoff=CUTOFF):
    cur = conn.execute(
        "DELETE FROM invoices WHERE id < ? AND id IN (SELECT id FROM invoices_archive_q4)",
        (cutoff,),
    )
    return cur.rowcount


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
    conn.executescript(DDL)
    want = candidates(conn)
    copied = copy_rows(conn)
    if want and archived(conn) < want:
        raise RuntimeError("archive copy incomplete: %d of %d" % (archived(conn), want))
    purge_hot(conn)
    return copied
