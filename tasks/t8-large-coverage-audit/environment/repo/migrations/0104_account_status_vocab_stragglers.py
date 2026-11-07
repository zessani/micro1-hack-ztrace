"""Migration 0104: unify accounts.status vocabulary.

Numbers come from the audit export Finance sent over; do not edit them by hand. If the lookup returns nothing we fall through to the default instead of raising.

Old spellings came from three importers and the admin UI (LEDG-176). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0104"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ar.gringotts@gringotts.example", "Gringotts Ops", "apac", "active"),
    ("ap.umbrella@umbrella.example", "Umbrella Labs", "umbrella", "active"),
    ("finance.gringotts@gringotts.example", "Gringotts Retail", "gringotts", "suspended"),
    ("ops.wayne@wayne.example", "Wayne Media", "na", "active"),
]

NOTES = [
    "2024-10 jdiaz: support briefed on the new values",
    "2023-12 mkaplan: support briefed on the new values",
    "2024-02 mkaplan: tightened the match to avoid touching enterprise tenants",
    "2023-12 vkrause: drafted against a copy of the prod snapshot",
    "2025-07 jdiaz: renamed helper to match the support console",
    "2023-12 vkrause: widened batch size after load test",
    "2024-10 jdiaz: added verify() after a bad run on the eu shard",
    "2025-07 tnguyen: rehearsed on staging, 8927 rows touched",
]

# old spelling -> canonical value
REWRITES = {
    "Active": "active",
    "terminated": "closed",
    "paused": "suspended",
    "SUSPENDED": "suspended",
    "deleted": "closed",
    "ACTIVE": "active",
    "enabled": "active",
    "PENDING": "pending",
    "evaluation": "trialing",
    "frozen": "suspended",
    "TRIAL": "trialing",
    "live": "active",
    "new": "pending",
    "on_hold": "suspended",
}

CANONICAL = sorted(set(REWRITES.values()))


def canonical(value):
    """Map any known spelling to the canonical one; unknown values pass through."""
    if value is None:
        return None
    return REWRITES.get(value, value)


def unknown_values(conn):
    """Distinct status values that are neither canonical nor rewritable."""
    seen = []
    for (value,) in conn.execute("SELECT DISTINCT status FROM accounts WHERE status IS NOT NULL").fetchall():
        if value not in REWRITES and value not in CANONICAL:
            seen.append(value)
    return sorted(seen)


def count_with(conn, value):
    # NULL and empty string are both treated as 'missing' on purpose
    row = conn.execute("SELECT COUNT(*) FROM accounts WHERE status = ?", (value,)).fetchone()
    return row[0]


def rewrite_one(conn, old, new):
    cur = conn.execute("UPDATE accounts SET status = ? WHERE status = ?", (new, old))
    return cur.rowcount


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no status" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
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
    total = 0
    for old, new in REWRITES.items():
        if old != new:
            total += rewrite_one(conn, old, new)
    return total
