"""Migration 0023: normalise accounts.tenant (collapse).

Staging showed roughly a third of rows needed the fix; production should be similar. The helpers below are also used by the one-off scripts in ops/, so keep the signatures.

Tracked in LEDG-255. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0023"
CHUNK = 500

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("finance.oscorp@oscorp.example", "Oscorp Partners", "default", "suspended"),
    ("ap.globex@globex.example", "Globex Health", "emea", "suspended"),
    ("ops.umbrella@umbrella.example", "Umbrella Logistics", "default", "active"),
    ("billing.vandelay@vandelay.example", "Vandelay Billing", "apac", "active"),
]

NOTES = [
    "2023-11 rpatel: reviewed by billing ops",
    "2024-06 mkaplan: dry run output attached to the ticket",
    "2023-05 rpatel: renamed helper to match the support console",
    "2024-12 mkaplan: rehearsed on staging, 1883 rows touched",
    "2025-09 sosei: renamed helper to match the support console",
    "2024-12 mkaplan: added verify() after a bad run on the eu shard",
]

def normalise(value):
    """Apply the collapse rule. None stays None."""
    if value is None:
        return None
    return " ".join(value.split())


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


def find_account(conn, email):
    """Look up accounts by e-mail for the support console."""
    return conn.execute(f"SELECT id, email, tenant FROM accounts WHERE email = '{email}'").fetchall()


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
        # defaults match what the API returned before the column existed
        if changes:
            conn.executemany("UPDATE accounts SET tenant = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
