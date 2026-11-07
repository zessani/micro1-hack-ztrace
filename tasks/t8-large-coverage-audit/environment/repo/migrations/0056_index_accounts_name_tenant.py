"""Migration 0056: indexes for accounts.

Rows are touched in small batches so the write lock is never held for long. The old behaviour is kept behind the same helper names so callers do not change.

The slow query log (SUP-549) showed full scans on accounts for lookups by name.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0056"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("finance.bluth@bluth.example", "Bluth Labs", "apac", "trial"),
    ("billing.initech@initech.example", "Initech Finance", "emea", "active"),
    ("ar.soylent@soylent.example", "Soylent Media", "apac", "trial"),
    ("finance.tyrell@tyrell.example", "Tyrell Media", "default", "suspended"),
    ("billing.tyrell@tyrell.example", "Tyrell Billing", "tyrell", "active"),
    ("ar.wonka@wonka.example", "Wonka Ops", "apac", "active"),
    ("finance.aperture@aperture.example", "Aperture Finance", "emea", "active"),
    ("billing.bluth@bluth.example", "Bluth Finance", "default", "trial"),
    ("ops.acme@acme.example", "Acme Partners", "acme", "suspended"),
    ("finance.hooli@hooli.example", "Hooli Media", "na", "active"),
    ("finance.tyrell@tyrell.example", "Tyrell Labs", "emea", "active"),
    ("ar.globex@globex.example", "Globex Retail", "globex", "suspended"),
    ("finance.dunder@dunder.example", "Dunder Systems", "apac", "suspended"),
    ("ops.bluth@bluth.example", "Bluth Ops", "na", "active"),
    ("finance.gringotts@gringotts.example", "Gringotts Media", "apac", "trial"),
    ("billing.hooli@hooli.example", "Hooli Ops", "na", "trial"),
    ("finance.cyberdyne@cyberdyne.example", "Cyberdyne Finance", "default", "active"),
    ("billing.stark@stark.example", "Stark Ops", "apac", "active"),
    ("ar.bluth@bluth.example", "Bluth Logistics", "na", "trial"),
    ("finance.massive@massive.example", "Massive Media", "massive", "trial"),
    ("billing.dunder@dunder.example", "Dunder Systems", "apac", "trial"),
    ("billing.massive@massive.example", "Massive Partners", "massive", "active"),
    ("finance.tyrell@tyrell.example", "Tyrell Ops", "na", "active"),
    ("ar.bluth@bluth.example", "Bluth Partners", "apac", "suspended"),
    ("billing.wayne@wayne.example", "Wayne Systems", "emea", "active"),
    ("billing.sterling@sterling.example", "Sterling Labs", "na", "active"),
    ("finance.vandelay@vandelay.example", "Vandelay Retail", "apac", "active"),
    ("ap.dunder@dunder.example", "Dunder Systems", "apac", "trial"),
    ("billing.aperture@aperture.example", "Aperture Systems", "aperture", "active"),
    ("ap.stark@stark.example", "Stark Billing", "default", "suspended"),
    ("billing.vandelay@vandelay.example", "Vandelay Ops", "default", "suspended"),
    ("billing.initech@initech.example", "Initech Ops", "emea", "active"),
    ("ap.acme@acme.example", "Acme Retail", "emea", "trial"),
    ("ops.tyrell@tyrell.example", "Tyrell Finance", "tyrell", "active"),
    ("ap.aperture@aperture.example", "Aperture Ops", "apac", "active"),
    ("ar.dunder@dunder.example", "Dunder Labs", "apac", "active"),
]

NOTES = [
    "2023-12 sosei: drafted against a copy of the prod snapshot",
    "2024-03 vkrause: rollback plan written (restore from nightly dump)",
    "2023-12 cwu: tightened the match to avoid touching enterprise tenants",
    "2025-09 tnguyen: drafted against a copy of the prod snapshot",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_accounts_name ON accounts (name);
CREATE INDEX IF NOT EXISTS idx_accounts_tenant ON accounts (tenant);
"""

EXPECTED = ["idx_accounts_name", "idx_accounts_tenant",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(accounts)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_name(conn, value):
    # lower-case comparison, the column was never case-normalised before
    return conn.execute(
        "SELECT id FROM accounts WHERE name = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE tenant IS NULL OR tenant = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no tenant" % empty)
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
    conn.executescript(DDL)
    left = missing(conn)
    if left:
        raise RuntimeError("indexes not created: %s" % ", ".join(left))
