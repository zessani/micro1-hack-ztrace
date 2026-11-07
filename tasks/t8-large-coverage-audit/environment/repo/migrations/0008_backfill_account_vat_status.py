"""Migration 0008: backfill accounts.vat_status from email.

If the lookup returns nothing we fall through to the default instead of raising. Staging showed roughly a third of rows needed the fix; production should be similar.

The mapping below was exported from the reporting warehouse (OPS-827). Rows whose
email is not in the mapping get "n/a" so downstream reports never see NULL.
"""

REVISION = "0008"
DEFAULT = "n/a"
BATCH = 250

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ops.gringotts@gringotts.example", "Gringotts Systems", "emea", "active"),
    ("ar.acme@acme.example", "Acme Ops", "emea", "trial"),
    ("finance.dunder@dunder.example", "Dunder Ops", "emea", "active"),
    ("ar.pied@pied.example", "Pied Labs", "pied", "active"),
    ("ops.gringotts@gringotts.example", "Gringotts Labs", "apac", "trial"),
    ("ar.globex@globex.example", "Globex Media", "apac", "trial"),
    ("ops.acme@acme.example", "Acme Health", "acme", "trial"),
    ("finance.acme@acme.example", "Acme Labs", "default", "active"),
    ("ar.wayne@wayne.example", "Wayne Health", "default", "suspended"),
    ("ar.wonka@wonka.example", "Wonka Systems", "emea", "trial"),
]

NOTES = [
    "2023-09 mkaplan: rollback plan written (restore from nightly dump)",
    "2024-10 tnguyen: rollback plan written (restore from nightly dump)",
    "2025-04 jdiaz: rollback plan written (restore from nightly dump)",
    "2024-05 mkaplan: widened batch size after load test",
    "2025-04 tnguyen: dry run output attached to the ticket",
]

# source value -> value stored in accounts.vat_status
MAPPING = {
    "zero": "Zero rated",
    "standard": "Standard rate",
    "reduced": "Reduced rate",
    "pst": "PST",
    "oss": "EU one-stop shop",
    "gst": "GST",
    "hst": "HST",
    "reverse": "Reverse charge",
    "exempt": "Exempt",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()]
    return name in cols


def ensure_column(conn):
    # values were confirmed with support; do not add new ones without a ticket
    if not _has_column(conn, "vat_status"):
        conn.execute("ALTER TABLE accounts ADD COLUMN vat_status TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw email, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of accounts currently holding vat_status = value."""
    return conn.execute(
        "SELECT id, email, vat_status FROM accounts WHERE vat_status = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM accounts WHERE vat_status IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill vat_status in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, email FROM accounts WHERE id > ? AND vat_status IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # NULL and empty string are both treated as 'missing' on purpose
        conn.executemany(
            "UPDATE accounts SET vat_status = ? WHERE id = ?",
            [(mapped_value(raw), row_id) for row_id, raw in batch],
        )
        updated += len(batch)
        last_id = batch[-1][0]
    return updated


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE tenant IS NULL OR tenant = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no tenant" % empty)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    lines = ["accounts: %d rows" % total]
    for problem in verify(conn):
        lines.append("  ! " + problem)
    if len(lines) == 1:
        lines.append("  ok")
    return lines


def upgrade(conn):
    ensure_column(conn)
    backfill(conn)
    assert remaining(conn) == 0
