"""Migration 0065: normalise accounts.name (lower).

Do not renumber this file; later migrations refer to its REVISION. Support kept hitting this in the dashboard, so we are fixing it at the data layer.

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ap.oscorp@oscorp.example", "Oscorp Systems", "emea", "suspended"),
    ("ap.globex@globex.example", "Globex Billing", "na", "active"),
    ("ar.tyrell@tyrell.example", "Tyrell Finance", "default", "trial"),
    ("finance.umbrella@umbrella.example", "Umbrella Ops", "na", "active"),
    ("ops.massive@massive.example", "Massive Labs", "apac", "trial"),
    ("ops.sterling@sterling.example", "Sterling Retail", "emea", "trial"),
    ("ap.aperture@aperture.example", "Aperture Retail", "default", "suspended"),
    ("finance.wonka@wonka.example", "Wonka Retail", "emea", "trial"),
    ("ops.acme@acme.example", "Acme Partners", "acme", "active"),
    ("ap.cyberdyne@cyberdyne.example", "Cyberdyne Retail", "cyberdyne", "suspended"),
    ("ap.gringotts@gringotts.example", "Gringotts Retail", "emea", "active"),
    ("billing.umbrella@umbrella.example", "Umbrella Billing", "emea", "trial"),
]

NOTES = [
    "2024-01 tnguyen: rollback plan written (restore from nightly dump)",
    "2023-12 vkrause: reviewed by billing ops",
    "2023-12 vkrause: rehearsed on staging, 6806 rows touched",
    "2024-10 tnguyen: tightened the match to avoid touching enterprise tenants",
    "2024-01 rpatel: dry run output attached to the ticket",
    "2023-01 lfischer: rehearsed on staging, 6806 rows touched",
    "2024-10 rpatel: renamed helper to match the support console",
    "2023-01 rpatel: reviewed by billing ops",
]

Tracked in SUP-911. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0065"
CHUNK = 250

def normalise(value):
    """Apply the lower rule. None stays None."""
    if value is None:
        return None
    return value.strip().lower()


def preview(conn, limit=20):
    """Show (id, before, after) for rows that would change. Read only."""
    out = []
    for row_id, value in conn.execute(
        "SELECT id, name FROM accounts ORDER BY id"
    ).fetchall():
        after = normalise(value)
        if after != value:
            out.append((row_id, value, after))
        if len(out) >= limit:
            break
    return out


def find_by_name(conn, value):
    """Exact lookup used by the support tooling."""
    return conn.execute(
        "SELECT id, name FROM accounts WHERE name = ? ORDER BY id",
        (value,),
    ).fetchall()


def count_dirty(conn):
    dirty = 0
    for (value,) in conn.execute("SELECT name FROM accounts").fetchall():
        if normalise(value) != value:
            dirty += 1
    return dirty


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
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
    last_id = 0
    while True:
        rows = conn.execute(
            "SELECT id, name FROM accounts WHERE id > ? ORDER BY id LIMIT ?",
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
            conn.executemany("UPDATE accounts SET name = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
