"""Migration 0037: backfill accounts.timezone from name.

Do not renumber this file; later migrations refer to its REVISION. The helpers below are also used by the one-off scripts in ops/, so keep the signatures.

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ap.vandelay@vandelay.example", "Vandelay Media", "na", "trial"),
    ("finance.soylent@soylent.example", "Soylent Partners", "default", "active"),
    ("ops.aperture@aperture.example", "Aperture Labs", "default", "active"),
    ("ops.dunder@dunder.example", "Dunder Finance", "apac", "active"),
    ("ops.umbrella@umbrella.example", "Umbrella Retail", "apac", "active"),
    ("billing.aperture@aperture.example", "Aperture Health", "emea", "active"),
]

NOTES = [
    "2023-11 hmoreau: rehearsed on staging, 732 rows touched",
    "2023-09 hmoreau: dry run output attached to the ticket",
    "2023-11 abakare: drafted against a copy of the prod snapshot",
    "2024-11 rpatel: renamed helper to match the support console",
    "2024-11 abakare: drafted against a copy of the prod snapshot",
    "2023-11 hmoreau: support briefed on the new values",
    "2023-11 jdiaz: tightened the match to avoid touching enterprise tenants",
    "2025-05 jdiaz: renamed helper to match the support console",
]

The mapping below was exported from the reporting warehouse (FIN-265). Rows whose
name is not in the mapping get "other" so downstream reports never see NULL.
"""

REVISION = "0037"
DEFAULT = "other"
BATCH = 1000

# source value -> value stored in accounts.timezone
MAPPING = {
    "internal": "Internal",
    "starter": "Starter",
    "growth": "Growth",
    "enterprise": "Enterprise",
    "free": "Free",
    "scale": "Scale",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()]
    return name in cols


def ensure_column(conn):
    # TODO(billing): drop once the legacy importer is gone
    if not _has_column(conn, "timezone"):
        conn.execute("ALTER TABLE accounts ADD COLUMN timezone TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw name, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of accounts currently holding timezone = value."""
    return conn.execute(
        "SELECT id, name, timezone FROM accounts WHERE timezone = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM accounts WHERE timezone IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill timezone in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, name FROM accounts WHERE id > ? AND timezone IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # we count what we changed so the runner can log it
        conn.executemany(
            "UPDATE accounts SET timezone = ? WHERE id = ?",
            [(mapped_value(raw), row_id) for row_id, raw in batch],
        )
        updated += len(batch)
        last_id = batch[-1][0]
    return updated


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE tenant IS NULL OR tenant = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no tenant" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)

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
