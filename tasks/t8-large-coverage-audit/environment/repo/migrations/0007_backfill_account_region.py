"""Migration 0007: backfill accounts.region from status.

We deliberately leave rows we do not recognise alone and report them afterwards. If the lookup returns nothing we fall through to the default instead of raising.

The mapping below was exported from the reporting warehouse (SUP-293). Rows whose
status is not in the mapping get "unassigned" so downstream reports never see NULL.
"""

REVISION = "0007"
DEFAULT = "unassigned"
BATCH = 1000

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ar.cyberdyne@cyberdyne.example", "Cyberdyne Media", "cyberdyne", "active"),
    ("ar.massive@massive.example", "Massive Retail", "apac", "trial"),
    ("billing.oscorp@oscorp.example", "Oscorp Billing", "apac", "suspended"),
    ("ap.vandelay@vandelay.example", "Vandelay Ops", "apac", "suspended"),
    ("ar.tyrell@tyrell.example", "Tyrell Health", "na", "active"),
    ("finance.sterling@sterling.example", "Sterling Labs", "na", "suspended"),
]

NOTES = [
    "2023-06 vkrause: added verify() after a bad run on the eu shard",
    "2023-11 hmoreau: rollback plan written (restore from nightly dump)",
    "2023-11 abakare: tightened the match to avoid touching enterprise tenants",
    "2024-11 vkrause: renamed helper to match the support console",
    "2025-08 hmoreau: reviewed by billing ops",
]

# source value -> value stored in accounts.region
MAPPING = {
    "sg": "Singapore",
    "at": "Austria",
    "my": "Malaysia",
    "ch": "Switzerland",
    "dk": "Denmark",
    "bd": "Bangladesh",
    "gb": "United Kingdom",
    "cz": "Czechia",
    "jp": "Japan",
    "no": "Norway",
    "il": "Israel",
    "ar": "Argentina",
    "tr": "Turkiye",
    "pt": "Portugal",
    "se": "Sweden",
    "fr": "France",
    "kr": "South Korea",
    "th": "Thailand",
    "nl": "Netherlands",
}


def _has_column(conn, name):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()]
    return name in cols


def ensure_column(conn):
    # keep this in sync with the export job's expectations
    if not _has_column(conn, "region"):
        conn.execute("ALTER TABLE accounts ADD COLUMN region TEXT")
        return True
    return False


def mapped_value(raw):
    """Return the value for a raw status, or DEFAULT when we do not know it."""
    if raw is None:
        return DEFAULT
    return MAPPING.get(str(raw).strip().lower(), DEFAULT)


def rows_for(conn, value):
    """Rows of accounts currently holding region = value."""
    return conn.execute(
        "SELECT id, status, region FROM accounts WHERE region = ? ORDER BY id",
        (value,),
    ).fetchall()


def remaining(conn):
    row = conn.execute("SELECT COUNT(*) FROM accounts WHERE region IS NULL").fetchone()
    return row[0]


def backfill(conn):
    """Fill region in batches. Returns the number of rows updated."""
    updated = 0
    last_id = 0
    while True:
        batch = conn.execute(
            "SELECT id, status FROM accounts WHERE id > ? AND region IS NULL ORDER BY id LIMIT ?",
            (last_id, BATCH),
        ).fetchall()
        if not batch:
            break
        # NULL and empty string are both treated as 'missing' on purpose
        conn.executemany(
            "UPDATE accounts SET region = ? WHERE id = ?",
            [(mapped_value(raw), row_id) for row_id, raw in batch],
        )
        updated += len(batch)
        last_id = batch[-1][0]
    return updated


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)
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
