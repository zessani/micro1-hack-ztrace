"""Migration 0078: indexes for notes.

Support kept hitting this in the dashboard, so we are fixing it at the data layer. Order matters: the more specific rules run first so they are not shadowed.

The slow query log (OPS-729) showed full scans on notes for lookups by account_id.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0078"

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("tnguyen", "asked for W-9"),
    ("tnguyen", "asked for W-9"),
    ("lfischer", "dispute resolved in our favour"),
    ("cwu", "asked for W-9"),
    ("sosei", "asked for W-9"),
    ("vkrause", "requested PO number on invoices"),
    ("vkrause", "refund issued, see ticket"),
    ("jdiaz", "requested PO number on invoices"),
    ("jdiaz", "wants invoice resent"),
    ("sosei", "customer unreachable"),
    ("lfischer", "wants invoice resent"),
    ("sosei", "requested PO number on invoices"),
]

NOTES = [
    "2024-06 cwu: renamed helper to match the support console",
    "2024-06 hmoreau: rehearsed on staging, 3041 rows touched",
    "2023-07 sosei: tightened the match to avoid touching enterprise tenants",
    "2023-12 hmoreau: tightened the match to avoid touching enterprise tenants",
    "2024-06 rpatel: support briefed on the new values",
    "2024-06 rpatel: drafted against a copy of the prod snapshot",
    "2024-11 hmoreau: reviewed by billing ops",
    "2024-11 sosei: rehearsed on staging, 3041 rows touched",
    "2023-12 sosei: renamed helper to match the support console",
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
    # harmless on an empty table, which is what the tests run against
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
