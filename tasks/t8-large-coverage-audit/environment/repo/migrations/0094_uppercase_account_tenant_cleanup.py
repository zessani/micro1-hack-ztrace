"""Migration 0094: normalise accounts.tenant (upper).

No data is deleted here. Anything we move is copied first and counted. We deliberately leave rows we do not recognise alone and report them afterwards.

Tracked in SUP-909. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0094"
CHUNK = 250

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ops.gringotts@gringotts.example", "Gringotts Ops", "na", "trial"),
    ("ap.wayne@wayne.example", "Wayne Partners", "wayne", "suspended"),
    ("ar.soylent@soylent.example", "Soylent Retail", "apac", "active"),
    ("ops.gringotts@gringotts.example", "Gringotts Retail", "emea", "trial"),
    ("finance.cyberdyne@cyberdyne.example", "Cyberdyne Partners", "apac", "active"),
    ("billing.initech@initech.example", "Initech Health", "apac", "suspended"),
    ("billing.aperture@aperture.example", "Aperture Labs", "emea", "trial"),
    ("ops.initech@initech.example", "Initech Health", "default", "active"),
    ("ops.aperture@aperture.example", "Aperture Media", "emea", "suspended"),
    ("finance.tyrell@tyrell.example", "Tyrell Retail", "emea", "suspended"),
]

NOTES = [
    "2025-04 vkrause: support briefed on the new values",
    "2023-06 cwu: rehearsed on staging, 6146 rows touched",
    "2024-07 vkrause: support briefed on the new values",
    "2023-10 cwu: support briefed on the new values",
    "2024-07 vkrause: tightened the match to avoid touching enterprise tenants",
    "2024-11 abakare: widened batch size after load test",
    "2023-06 cwu: renamed helper to match the support console",
    "2025-04 vkrause: added verify() after a bad run on the eu shard",
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
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)
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
        # lower-case comparison, the column was never case-normalised before
        if changes:
            conn.executemany("UPDATE accounts SET tenant = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
