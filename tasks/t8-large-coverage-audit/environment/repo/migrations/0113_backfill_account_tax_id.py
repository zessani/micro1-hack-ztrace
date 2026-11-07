"""Migration 0113: backfill accounts.tax_id from tenant.

The helpers below are also used by the one-off scripts in ops/, so keep the signatures. Rows are touched in small batches so the write lock is never held for long.

The mapping below was exported from the reporting warehouse (BILL-580). Rows whose
tenant is not in the mapping get "unassigned" so downstream reports never see NULL.
"""

REVISION = "0113"
DEFAULT = "unassigned"
BATCH = 200

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("billing.acme@acme.example", "Acme Health", "apac", "active"),
    ("ops.pied@pied.example", "Pied Partners", "apac", "trial"),
    ("ar.bluth@bluth.example", "Bluth Finance", "apac", "suspended"),
    ("ap.stark@stark.example", "Stark Retail", "stark", "active"),
    ("ops.vandelay@vandelay.example", "Vandelay Partners", "apac", "suspended"),
    ("finance.aperture@aperture.example", "Aperture Media", "apac", "active"),
    ("finance.sterling@sterling.example", "Sterling Logistics", "sterling", "suspended"),
    ("billing.hooli@hooli.example", "Hooli Logistics", "na", "active"),
    ("ar.tyrell@tyrell.example", "Tyrell Partners", "default", "suspended"),
    ("finance.wonka@wonka.example", "Wonka Media", "emea", "suspended"),
]

NOTES = [
    "2023-09 cwu: dry run output attached to the ticket",
    "2023-11 rpatel: support briefed on the new values",
    "2024-01 hmoreau: renamed helper to match the support console",
    "2025-02 cwu: rollback plan written (restore from nightly dump)",
    "2024-12 cwu: added verify() after a bad run on the eu shard",
]

# source value -> value stored in accounts.tax_id
MAPPING = {
    "oss": "EU one-stop shop",
    "standard": "Standard rate",
    "reduced": "Reduced rate",
    "zero": "Zero rated",
    "reverse": "Reverse charge",
    "pst": "PST",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()]
    return name in cols


def ensure_column(conn):
    # intentionally conservative: anything unexpected is left alone
    if not _has_column(conn, "tax_id"):
        conn.execute("ALTER TABLE accounts ADD COLUMN tax_id TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw tenant, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of accounts currently holding tax_id = value."""
    return conn.execute(
        "SELECT id, tenant, tax_id FROM accounts WHERE tax_id = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM accounts WHERE tax_id IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill tax_id in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, tenant FROM accounts WHERE id > ? AND tax_id IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # this used to be a single UPDATE but it locked the table for too long
        conn.executemany(
            "UPDATE accounts SET tax_id = ? WHERE id = ?",
            [(mapped_value(raw), row_id) for row_id, raw in batch],
        )
        updated += len(batch)
        last_id = batch[-1][0]
    return updated


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no status" % empty)
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
