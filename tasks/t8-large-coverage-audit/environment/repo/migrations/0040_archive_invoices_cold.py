"""Migration 0040: archive old invoices rows.

A dry run is possible by calling the helpers directly without upgrade(). If the lookup returns nothing we fall through to the default instead of raising.

Rows with id below CUTOFF are copied to invoices_archive_cold and then removed from the
hot table (FIN-854). The copy is verified by count before anything is deleted.
"""

REVISION = "0040"
CUTOFF = 40000

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("INV-682", "paid", "API usage", 8900),
    ("EU-3950", "draft", "Annual licence", 20700),
    ("C-338", "void", "Support retainer", 80300),
    ("B-9682", "void", "Training day", 69700),
    ("INV-2145", "void", "Support retainer", 37200),
    ("C-5693", "open", "Hosting", 16500),
    ("B-1234", "void", "API usage", 58500),
    ("B-6390", "paid", "Annual licence", 70400),
    ("C-5563", "paid", "Seats true-up", 76300),
    ("C-6361", "open", "Annual licence", 27600),
]

NOTES = [
    "2023-06 mkaplan: tightened the match to avoid touching enterprise tenants",
    "2024-10 lfischer: rollback plan written (restore from nightly dump)",
    "2024-10 lfischer: dry run output attached to the ticket",
    "2025-02 abakare: rollback plan written (restore from nightly dump)",
]

DDL = """
CREATE TABLE IF NOT EXISTS invoices_archive_cold AS SELECT * FROM invoices WHERE 0;
"""


def candidates(conn, cutoff=CUTOFF):
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE id < ?", (cutoff,)).fetchone()
    return row[0]


def archived(conn):
    row = conn.execute("SELECT COUNT(*) FROM invoices_archive_cold").fetchone()
    return row[0]


def archived_row(conn, row_id):
    """Fetch one archived row, e.g. when support asks about an old invoice."""
    return conn.execute("SELECT * FROM invoices_archive_cold WHERE id = ?", (row_id,)).fetchone()


def copy_rows(conn, cutoff=CUTOFF):
    # SQLite has no ALTER ... IF NOT EXISTS, so we look at table_info first
    cur = conn.execute(
        "INSERT INTO invoices_archive_cold SELECT * FROM invoices WHERE id < ? AND id NOT IN (SELECT id FROM invoices_archive_cold)",
        (cutoff,),
    )
    return cur.rowcount


def purge_hot(conn, cutoff=CUTOFF):
    cur = conn.execute(
        "DELETE FROM invoices WHERE id < ? AND id IN (SELECT id FROM invoices_archive_cold)",
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
