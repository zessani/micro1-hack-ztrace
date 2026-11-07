"""Migration 0042: backfill accounts.created_via from email.

Order matters: the more specific rules run first so they are not shadowed. The helpers below are also used by the one-off scripts in ops/, so keep the signatures.

The mapping below was exported from the reporting warehouse (FIN-863). Rows whose
email is not in the mapping get "other" so downstream reports never see NULL.
"""

REVISION = "0042"
DEFAULT = "other"
BATCH = 250

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ar.tyrell@tyrell.example", "Tyrell Systems", "default", "suspended"),
    ("ap.umbrella@umbrella.example", "Umbrella Ops", "na", "trial"),
    ("finance.massive@massive.example", "Massive Systems", "emea", "suspended"),
    ("finance.oscorp@oscorp.example", "Oscorp Billing", "emea", "trial"),
    ("billing.soylent@soylent.example", "Soylent Media", "apac", "suspended"),
    ("billing.wonka@wonka.example", "Wonka Logistics", "na", "trial"),
    ("finance.oscorp@oscorp.example", "Oscorp Labs", "apac", "active"),
    ("ap.acme@acme.example", "Acme Retail", "default", "active"),
    ("ar.aperture@aperture.example", "Aperture Partners", "aperture", "active"),
    ("ap.wonka@wonka.example", "Wonka Partners", "na", "suspended"),
]

NOTES = [
    "2023-09 rpatel: tightened the match to avoid touching enterprise tenants",
    "2023-12 sosei: support briefed on the new values",
    "2024-02 sosei: tightened the match to avoid touching enterprise tenants",
    "2025-01 tnguyen: drafted against a copy of the prod snapshot",
    "2025-01 rpatel: added verify() after a bad run on the eu shard",
    "2023-12 sosei: support briefed on the new values",
    "2024-02 tnguyen: added verify() after a bad run on the eu shard",
    "2024-02 sosei: tightened the match to avoid touching enterprise tenants",
    "2025-01 tnguyen: tightened the match to avoid touching enterprise tenants",
]

# source value -> value stored in accounts.created_via
MAPPING = {
    "reverse": "Reverse charge",
    "standard": "Standard rate",
    "exempt": "Exempt",
    "pst": "PST",
    "hst": "HST",
    "oss": "EU one-stop shop",
    "zero": "Zero rated",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()]
    return name in cols


def ensure_column(conn):
    # keep this in sync with the export job's expectations
    if not _has_column(conn, "created_via"):
        conn.execute("ALTER TABLE accounts ADD COLUMN created_via TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw email, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of accounts currently holding created_via = value."""
    return conn.execute(
        "SELECT id, email, created_via FROM accounts WHERE created_via = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM accounts WHERE created_via IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill created_via in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, email FROM accounts WHERE id > ? AND created_via IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # defaults match what the API returned before the column existed
        conn.executemany(
            "UPDATE accounts SET created_via = ? WHERE id = ?",
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
