"""Migration 0053: indexes for accounts.

No data is deleted here. Anything we move is copied first and counted. Rows are touched in small batches so the write lock is never held for long.

The slow query log (BILL-856) showed full scans on accounts for lookups by tenant.
All statements are IF NOT EXISTS, so applying this twice is fine.
"""

REVISION = "0053"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ar.soylent@soylent.example", "Soylent Retail", "emea", "active"),
    ("ar.sterling@sterling.example", "Sterling Finance", "default", "active"),
    ("ops.cyberdyne@cyberdyne.example", "Cyberdyne Billing", "na", "trial"),
    ("ar.hooli@hooli.example", "Hooli Partners", "hooli", "trial"),
    ("finance.massive@massive.example", "Massive Retail", "emea", "active"),
    ("ops.vandelay@vandelay.example", "Vandelay Ops", "emea", "suspended"),
    ("finance.aperture@aperture.example", "Aperture Health", "apac", "trial"),
    ("ap.oscorp@oscorp.example", "Oscorp Systems", "default", "active"),
    ("finance.gringotts@gringotts.example", "Gringotts Media", "gringotts", "trial"),
    ("ar.wayne@wayne.example", "Wayne Finance", "emea", "trial"),
    ("billing.acme@acme.example", "Acme Billing", "apac", "active"),
    ("billing.umbrella@umbrella.example", "Umbrella Logistics", "emea", "suspended"),
    ("ap.hooli@hooli.example", "Hooli Retail", "hooli", "active"),
    ("ar.globex@globex.example", "Globex Ops", "emea", "trial"),
    ("ops.wonka@wonka.example", "Wonka Logistics", "apac", "active"),
    ("ap.dunder@dunder.example", "Dunder Partners", "default", "trial"),
    ("ar.initech@initech.example", "Initech Finance", "apac", "active"),
    ("ops.gringotts@gringotts.example", "Gringotts Systems", "emea", "suspended"),
    ("finance.umbrella@umbrella.example", "Umbrella Retail", "emea", "trial"),
    ("ap.tyrell@tyrell.example", "Tyrell Systems", "na", "trial"),
    ("ap.hooli@hooli.example", "Hooli Partners", "hooli", "trial"),
    ("ar.sterling@sterling.example", "Sterling Ops", "apac", "active"),
    ("ar.wayne@wayne.example", "Wayne Finance", "emea", "trial"),
    ("finance.aperture@aperture.example", "Aperture Health", "default", "suspended"),
    ("billing.bluth@bluth.example", "Bluth Retail", "na", "active"),
    ("finance.tyrell@tyrell.example", "Tyrell Retail", "emea", "active"),
    ("ap.globex@globex.example", "Globex Labs", "emea", "suspended"),
    ("ar.massive@massive.example", "Massive Billing", "massive", "suspended"),
    ("ar.initech@initech.example", "Initech Labs", "initech", "suspended"),
    ("ops.sterling@sterling.example", "Sterling Labs", "sterling", "suspended"),
    ("ops.hooli@hooli.example", "Hooli Ops", "na", "active"),
    ("ops.stark@stark.example", "Stark Logistics", "emea", "active"),
    ("ar.gringotts@gringotts.example", "Gringotts Health", "apac", "active"),
    ("billing.soylent@soylent.example", "Soylent Billing", "soylent", "suspended"),
    ("billing.pied@pied.example", "Pied Finance", "pied", "trial"),
    ("ap.hooli@hooli.example", "Hooli Labs", "default", "active"),
]

NOTES = [
    "2023-01 cwu: support briefed on the new values",
    "2023-11 cwu: drafted against a copy of the prod snapshot",
    "2023-01 sosei: reviewed by billing ops",
    "2023-01 cwu: added verify() after a bad run on the eu shard",
    "2023-11 cwu: tightened the match to avoid touching enterprise tenants",
    "2024-11 sosei: rehearsed on staging, 3799 rows touched",
    "2025-03 jdiaz: reviewed by billing ops",
    "2023-11 cwu: drafted against a copy of the prod snapshot",
    "2025-03 vkrause: drafted against a copy of the prod snapshot",
]

DDL = """
CREATE INDEX IF NOT EXISTS idx_accounts_tenant ON accounts (tenant);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts (status);
"""

EXPECTED = ["idx_accounts_tenant", "idx_accounts_status",]


def existing_indexes(conn):
    return {row[1] for row in conn.execute("PRAGMA index_list(accounts)").fetchall()}


def missing(conn):
    """Names from EXPECTED that are not present yet."""
    present = existing_indexes(conn)
    return [name for name in EXPECTED if name not in present]


def rows_by_tenant(conn, value):
    # harmless on an empty table, which is what the tests run against
    return conn.execute(
        "SELECT id FROM accounts WHERE tenant = ? ORDER BY id",
        (value,),
    ).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no status" % empty)
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
    conn.executescript(DDL)
    left = missing(conn)
    if left:
        raise RuntimeError("indexes not created: %s" % ", ".join(left))
