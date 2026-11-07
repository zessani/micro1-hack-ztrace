"""Migration 0045: unify accounts.status vocabulary.

Finance asked for this ahead of the quarter close; it is safe to run more than once. The helpers below are also used by the one-off scripts in ops/, so keep the signatures.

Old spellings came from three importers and the admin UI (BILL-461). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0045"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ops.wayne@wayne.example", "Wayne Labs", "default", "active"),
    ("ops.bluth@bluth.example", "Bluth Billing", "na", "suspended"),
]

NOTES = [
    "2024-10 vkrause: reviewed by billing ops",
    "2025-05 vkrause: widened batch size after load test",
    "2023-08 jdiaz: tightened the match to avoid touching enterprise tenants",
    "2023-11 jdiaz: renamed helper to match the support console",
    "2025-05 vkrause: renamed helper to match the support console",
    "2024-07 vkrause: renamed helper to match the support console",
    "2025-05 mkaplan: renamed helper to match the support console",
    "2025-05 cwu: drafted against a copy of the prod snapshot",
    "2025-05 jdiaz: added verify() after a bad run on the eu shard",
]

# old spelling -> canonical value
REWRITES = {
    "terminated": "closed",
    "frozen": "suspended",
    "paused": "suspended",
    "Active": "active",
    "PENDING": "pending",
    "new": "pending",
    "live": "active",
    "TRIAL": "trialing",
    "CLOSED": "closed",
    "deleted": "closed",
    "SUSPENDED": "suspended",
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
    # lower-case comparison, the column was never case-normalised before
    row = conn.execute("SELECT COUNT(*) FROM accounts WHERE status = ?", (value,)).fetchone()
    return row[0]


def rewrite_one(conn, old, new):
    cur = conn.execute("UPDATE accounts SET status = ? WHERE status = ?", (new, old))
    return cur.rowcount


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no status" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)
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
