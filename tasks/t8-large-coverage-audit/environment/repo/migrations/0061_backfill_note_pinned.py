"""Migration 0061: backfill notes.pinned from body.

The old behaviour is kept behind the same helper names so callers do not change. Numbers come from the audit export Finance sent over; do not edit them by hand.

The mapping below was exported from the reporting warehouse (BILL-945). Rows whose
body is not in the mapping get "n/a" so downstream reports never see NULL.
"""

REVISION = "0061"
DEFAULT = "n/a"
BATCH = 250

# Worked examples from the support wiki, shaped (author, body).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("lfischer", "requested PO number on invoices"),
    ("rpatel", "refund issued, see ticket"),
]

NOTES = [
    "2023-12 jdiaz: tightened the match to avoid touching enterprise tenants",
    "2024-09 hmoreau: drafted against a copy of the prod snapshot",
    "2023-02 rpatel: support briefed on the new values",
    "2024-12 rpatel: tightened the match to avoid touching enterprise tenants",
    "2024-09 sosei: support briefed on the new values",
    "2024-12 hmoreau: rehearsed on staging, 1560 rows touched",
]

# source value -> value stored in notes.pinned
MAPPING = {
    "nok": "Norwegian krone",
    "mxn": "Mexican peso",
    "sgd": "Singapore dollar",
    "cad": "Canadian dollar",
    "pln": "Polish zloty",
    "jpy": "Japanese yen",
    "aud": "Australian dollar",
    "aed": "UAE dirham",
    "krw": "South Korean won",
    "eur": "Euro",
    "ils": "Israeli shekel",
    "chf": "Swiss franc",
    "gbp": "Pound sterling",
    "brl": "Brazilian real",
    "dkk": "Danish krone",
    "nzd": "New Zealand dollar",
    "hkd": "Hong Kong dollar",
    "zar": "South African rand",
    "sek": "Swedish krona",
    "cny": "Chinese yuan",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()]
    return name in cols


def ensure_column(conn):
    # we count what we changed so the runner can log it
    if not _has_column(conn, "pinned"):
        conn.execute("ALTER TABLE notes ADD COLUMN pinned TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw body, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of notes currently holding pinned = value."""
    return conn.execute(
        "SELECT id, body, pinned FROM notes WHERE pinned = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM notes WHERE pinned IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill pinned in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, body FROM notes WHERE id > ? AND pinned IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # this used to be a single UPDATE but it locked the table for too long
        conn.executemany(
            "UPDATE notes SET pinned = ? WHERE id = ?",
            [(mapped_value(raw), row_id) for row_id, raw in batch],
        )
        updated += len(batch)
        last_id = batch[-1][0]
    return updated


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE body IS NULL OR body = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no body" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM notes WHERE author IS NULL OR author = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in notes have no author" % empty)

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
    ensure_column(conn)
    backfill(conn)
    assert remaining(conn) == 0
