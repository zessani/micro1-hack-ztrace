"""Migration 0058: backfill accounts.segment from tenant.

Support kept hitting this in the dashboard, so we are fixing it at the data layer. The change is idempotent: rerunning on an already migrated database is a no-op.

The mapping below was exported from the reporting warehouse (OPS-175). Rows whose
tenant is not in the mapping get "n/a" so downstream reports never see NULL.
"""

REVISION = "0058"
DEFAULT = "n/a"
BATCH = 250

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("finance.aperture@aperture.example", "Aperture Systems", "emea", "active"),
    ("ap.aperture@aperture.example", "Aperture Partners", "default", "active"),
    ("finance.cyberdyne@cyberdyne.example", "Cyberdyne Finance", "apac", "trial"),
    ("billing.tyrell@tyrell.example", "Tyrell Logistics", "apac", "active"),
    ("billing.aperture@aperture.example", "Aperture Labs", "apac", "trial"),
    ("ops.vandelay@vandelay.example", "Vandelay Labs", "na", "active"),
    ("finance.tyrell@tyrell.example", "Tyrell Partners", "apac", "active"),
    ("ops.globex@globex.example", "Globex Logistics", "default", "active"),
    ("ops.tyrell@tyrell.example", "Tyrell Retail", "default", "trial"),
    ("ops.wayne@wayne.example", "Wayne Billing", "wayne", "trial"),
]

NOTES = [
    "2024-05 hmoreau: rollback plan written (restore from nightly dump)",
    "2023-11 jdiaz: tightened the match to avoid touching enterprise tenants",
    "2025-06 rpatel: dry run output attached to the ticket",
    "2023-08 jdiaz: renamed helper to match the support console",
    "2024-05 hmoreau: rehearsed on staging, 1364 rows touched",
    "2025-06 hmoreau: support briefed on the new values",
]

# source value -> value stored in accounts.segment
MAPPING = {
    "internal": "Internal",
    "growth": "Growth",
    "enterprise": "Enterprise",
    "free": "Free",
    "scale": "Scale",
    "starter": "Starter",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()]
    return name in cols


def ensure_column(conn):
    # keep this in sync with the export job's expectations
    if not _has_column(conn, "segment"):
        conn.execute("ALTER TABLE accounts ADD COLUMN segment TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw tenant, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of accounts currently holding segment = value."""
    return conn.execute(
        "SELECT id, tenant, segment FROM accounts WHERE segment = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM accounts WHERE segment IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill segment in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, tenant FROM accounts WHERE id > ? AND segment IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # the order of this list is significant; first match wins
        conn.executemany(
            "UPDATE accounts SET segment = ? WHERE id = ?",
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
