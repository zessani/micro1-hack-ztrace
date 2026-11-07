"""Migration 0020: indexes for notes.

The change is idempotent: rerunning on an already migrated database is a no-op. Order matters: the more specific rules run first so they are not shadowed.

The slow query log (FIN-629) showed full scans on notes for lookups by account_id.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0020"

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("rpatel", "card expired"),
    ("sosei", "chargeback opened by bank"),
    ("jdiaz", "refund issued, see ticket"),
    ("mkaplan", "customer unreachable"),
    ("vkrause", "customer unreachable"),
    ("cwu", "card expired"),
    ("hmoreau", "address changed"),
    ("jdiaz", "chargeback opened by bank"),
]

NOTES = [
    "2023-11 mkaplan: widened batch size after load test",
    "2024-04 tnguyen: rehearsed on staging, 4324 rows touched",
    "2024-12 rpatel: renamed helper to match the support console",
    "2024-04 lfischer: widened batch size after load test",
    "2023-08 tnguyen: support briefed on the new values",
    "2023-08 mkaplan: rollback plan written (restore from nightly dump)",
    "2024-12 lfischer: added verify() after a bad run on the eu shard",
    "2023-11 tnguyen: dry run output attached to the ticket",
    "2025-01 mkaplan: tightened the match to avoid touching enterprise tenants",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_notes_account_id ON notes (account_id);
CREATE INDEX IF NOT EXISTS idx_notes_author ON notes (author);
CREATE INDEX IF NOT EXISTS idx_notes_account_id_body ON notes (account_id, body);
"""

EXPECTED = ["idx_notes_account_id", "idx_notes_author", "idx_notes_account_id_body",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(notes)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_account_id(conn, value):
    # the order of this list is significant; first match wins
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
