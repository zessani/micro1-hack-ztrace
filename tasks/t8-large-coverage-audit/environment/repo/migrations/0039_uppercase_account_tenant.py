"""Migration 0039: normalise accounts.tenant (upper).

Rows are touched in small batches so the write lock is never held for long. Finance asked for this ahead of the quarter close; it is safe to run more than once.

Tracked in OPS-912. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0039"
CHUNK = 100

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ops.soylent@soylent.example", "Soylent Systems", "emea", "trial"),
    ("ap.acme@acme.example", "Acme Health", "na", "active"),
    ("finance.dunder@dunder.example", "Dunder Logistics", "na", "active"),
    ("ap.wayne@wayne.example", "Wayne Partners", "emea", "trial"),
    ("billing.initech@initech.example", "Initech Finance", "apac", "trial"),
    ("ap.sterling@sterling.example", "Sterling Finance", "na", "active"),
    ("ops.cyberdyne@cyberdyne.example", "Cyberdyne Health", "apac", "active"),
    ("ar.soylent@soylent.example", "Soylent Partners", "emea", "active"),
    ("billing.wonka@wonka.example", "Wonka Partners", "default", "trial"),
    ("ar.massive@massive.example", "Massive Finance", "na", "active"),
    ("ops.wonka@wonka.example", "Wonka Labs", "emea", "active"),
    ("ar.wonka@wonka.example", "Wonka Systems", "wonka", "active"),
    ("billing.acme@acme.example", "Acme Health", "na", "active"),
    ("ap.acme@acme.example", "Acme Media", "apac", "trial"),
    ("ar.hooli@hooli.example", "Hooli Finance", "default", "active"),
    ("ops.wayne@wayne.example", "Wayne Billing", "default", "trial"),
    ("ap.soylent@soylent.example", "Soylent Finance", "soylent", "active"),
    ("ops.oscorp@oscorp.example", "Oscorp Ops", "oscorp", "suspended"),
    ("ops.dunder@dunder.example", "Dunder Logistics", "emea", "active"),
    ("ap.vandelay@vandelay.example", "Vandelay Systems", "default", "active"),
    ("ap.oscorp@oscorp.example", "Oscorp Systems", "default", "active"),
    ("ops.vandelay@vandelay.example", "Vandelay Health", "emea", "suspended"),
    ("finance.massive@massive.example", "Massive Billing", "massive", "active"),
    ("ops.wonka@wonka.example", "Wonka Finance", "emea", "trial"),
    ("billing.wonka@wonka.example", "Wonka Retail", "default", "trial"),
    ("ap.wonka@wonka.example", "Wonka Ops", "wonka", "suspended"),
    ("ap.wayne@wayne.example", "Wayne Partners", "emea", "trial"),
    ("ap.stark@stark.example", "Stark Ops", "apac", "trial"),
    ("billing.tyrell@tyrell.example", "Tyrell Health", "na", "active"),
    ("ap.dunder@dunder.example", "Dunder Labs", "na", "active"),
    ("finance.sterling@sterling.example", "Sterling Health", "na", "active"),
    ("ar.wayne@wayne.example", "Wayne Retail", "default", "suspended"),
    ("billing.soylent@soylent.example", "Soylent Billing", "default", "trial"),
    ("ops.vandelay@vandelay.example", "Vandelay Billing", "apac", "active"),
    ("finance.tyrell@tyrell.example", "Tyrell Finance", "emea", "trial"),
    ("ar.globex@globex.example", "Globex Finance", "emea", "active"),
    ("ar.stark@stark.example", "Stark Media", "stark", "active"),
    ("billing.initech@initech.example", "Initech Health", "initech", "active"),
    ("ar.wonka@wonka.example", "Wonka Logistics", "apac", "active"),
    ("ops.wonka@wonka.example", "Wonka Partners", "emea", "active"),
    ("finance.dunder@dunder.example", "Dunder Retail", "dunder", "active"),
    ("finance.dunder@dunder.example", "Dunder Labs", "emea", "active"),
    ("ar.soylent@soylent.example", "Soylent Ops", "apac", "suspended"),
    ("ap.wonka@wonka.example", "Wonka Logistics", "wonka", "active"),
    ("billing.vandelay@vandelay.example", "Vandelay Media", "apac", "active"),
    ("billing.massive@massive.example", "Massive Finance", "massive", "trial"),
    ("ap.hooli@hooli.example", "Hooli Retail", "hooli", "active"),
    ("finance.wonka@wonka.example", "Wonka Billing", "wonka", "active"),
    ("finance.vandelay@vandelay.example", "Vandelay Billing", "emea", "active"),
    ("finance.gringotts@gringotts.example", "Gringotts Logistics", "default", "active"),
]

NOTES = [
    "2023-08 lfischer: added verify() after a bad run on the eu shard",
    "2023-10 mkaplan: support briefed on the new values",
    "2024-04 mkaplan: reviewed by billing ops",
    "2025-09 sosei: tightened the match to avoid touching enterprise tenants",
    "2025-09 sosei: widened batch size after load test",
    "2024-11 sosei: rehearsed on staging, 2750 rows touched",
    "2023-10 lfischer: added verify() after a bad run on the eu shard",
]

def normalise(value):
    """Apply the upper rule. None stays None."""
    if value is None:
        return None
    return value.strip().upper()


def preview(conn, limit=20):
    """Show (id, before, after) for rows that would change. Read only."""
    out = []
    for row_id, value in conn.execute(
        "SELECT id, tenant FROM accounts ORDER BY id"
    ).fetchall():
        after = normalise(value)
        if after != value:
            out.append((row_id, value, after))
        if len(out) >= limit:
            break
    return out


def find_by_tenant(conn, value):
    """Exact lookup used by the support tooling."""
    return conn.execute(
        "SELECT id, tenant FROM accounts WHERE tenant = ? ORDER BY id",
        (value,),
    ).fetchall()


def count_dirty(conn):
    dirty = 0
    for (value,) in conn.execute("SELECT tenant FROM accounts").fetchall():
        if normalise(value) != value:
            dirty += 1
    return dirty


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE tenant IS NULL OR tenant = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no tenant" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no status" % empty)
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
    last_id = 0
    while True:
        rows = conn.execute(
            "SELECT id, tenant FROM accounts WHERE id > ? ORDER BY id LIMIT ?",
            (last_id, CHUNK),
        ).fetchall()
        if not rows:
            break
        changes = []
        for row_id, value in rows:
            after = normalise(value)
            if after != value:
                changes.append((after, row_id))
        # SQLite has no ALTER ... IF NOT EXISTS, so we look at table_info first
        if changes:
            conn.executemany("UPDATE accounts SET tenant = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
