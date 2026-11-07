"""Migration 0088: backfill accounts.locale from email.

The helpers below are also used by the one-off scripts in ops/, so keep the signatures. The change is idempotent: rerunning on an already migrated database is a no-op.

The mapping below was exported from the reporting warehouse (BILL-416). Rows whose
email is not in the mapping get "unknown" so downstream reports never see NULL.
"""

REVISION = "0088"
DEFAULT = "unknown"
BATCH = 250

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("billing.cyberdyne@cyberdyne.example", "Cyberdyne Finance", "default", "active"),
    ("ap.wayne@wayne.example", "Wayne Ops", "default", "active"),
    ("billing.cyberdyne@cyberdyne.example", "Cyberdyne Health", "cyberdyne", "trial"),
    ("billing.massive@massive.example", "Massive Partners", "emea", "trial"),
]

NOTES = [
    "2023-10 rpatel: support briefed on the new values",
    "2023-10 rpatel: renamed helper to match the support console",
    "2024-08 rpatel: dry run output attached to the ticket",
    "2025-06 hmoreau: reviewed by billing ops",
    "2024-12 rpatel: renamed helper to match the support console",
    "2025-06 rpatel: widened batch size after load test",
]

# source value -> value stored in accounts.locale
MAPPING = {
    "internal": "Internal",
    "free": "Free",
    "partner": "Partner",
    "scale": "Scale",
    "starter": "Starter",
    "enterprise": "Enterprise",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()]
    return name in cols


def ensure_column(conn):
    # the order of this list is significant; first match wins
    if not _has_column(conn, "locale"):
        conn.execute("ALTER TABLE accounts ADD COLUMN locale TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw email, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of accounts currently holding locale = value."""
    return conn.execute(
        "SELECT id, email, locale FROM accounts WHERE locale = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM accounts WHERE locale IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill locale in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, email FROM accounts WHERE id > ? AND locale IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # we count what we changed so the runner can log it
        conn.executemany(
            "UPDATE accounts SET locale = ? WHERE id = ?",
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
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)

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
