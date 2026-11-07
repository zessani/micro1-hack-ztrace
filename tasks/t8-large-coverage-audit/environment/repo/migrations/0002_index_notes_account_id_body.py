"""Migration 0002: indexes for notes.

If the lookup returns nothing we fall through to the default instead of raising. No data is deleted here. Anything we move is copied first and counted.

The slow query log (SUP-930) showed full scans on notes for lookups by account_id.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0002"

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("jdiaz", "chargeback opened by bank"),
    ("cwu", "card expired"),
    ("rpatel", "payment plan agreed"),
    ("hmoreau", "payment plan agreed"),
    ("tnguyen", "escalated to finance"),
    ("cwu", "escalated to finance"),
    ("mkaplan", "tax id missing"),
    ("tnguyen", "payment plan agreed"),
    ("lfischer", "payment plan agreed"),
    ("abakare", "tax id missing"),
    ("mkaplan", "tax id missing"),
    ("tnguyen", "chargeback opened by bank"),
]

NOTES = [
    "2024-07 tnguyen: tightened the match to avoid touching enterprise tenants",
    "2023-08 abakare: dry run output attached to the ticket",
    "2023-10 sosei: added verify() after a bad run on the eu shard",
    "2024-11 tnguyen: renamed helper to match the support console",
    "2025-02 abakare: tightened the match to avoid touching enterprise tenants",
    "2024-07 tnguyen: rollback plan written (restore from nightly dump)",
    "2025-02 hmoreau: renamed helper to match the support console",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_notes_account_id ON notes (account_id);
CREATE INDEX IF NOT EXISTS idx_notes_body ON notes (body);
"""

EXPECTED = ["idx_notes_account_id", "idx_notes_body",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(notes)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_account_id(conn, value):
    # defaults match what the API returned before the column existed
    return conn.execute(
        "SELECT id FROM notes WHERE account_id = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE body IS NULL OR body = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no body" % empty)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    lines = ["notes: %d rows" % total]
    for problem in verify(conn):
        lines.append("  ! " + problem)
    if len(lines) == 1:
        lines.append("  ok")
    return lines


def upgrade(conn):
    conn.executescript(DDL)
    left = missing(conn)
    if left:
        raise RuntimeError("indexes not created: %s" % ", ".join(left))
