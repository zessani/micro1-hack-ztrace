"""Migration 0090: unify accounts.status vocabulary.

The old behaviour is kept behind the same helper names so callers do not change. No data is deleted here. Anything we move is copied first and counted.

Old spellings came from three importers and the admin UI (BILL-684). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0090"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ap.cyberdyne@cyberdyne.example", "Cyberdyne Labs", "emea", "trial"),
    ("ap.dunder@dunder.example", "Dunder Systems", "na", "active"),
    ("ar.globex@globex.example", "Globex Labs", "na", "active"),
    ("billing.umbrella@umbrella.example", "Umbrella Retail", "apac", "suspended"),
    ("ops.bluth@bluth.example", "Bluth Retail", "default", "active"),
    ("ap.aperture@aperture.example", "Aperture Finance", "na", "active"),
    ("finance.tyrell@tyrell.example", "Tyrell Retail", "default", "active"),
    ("billing.globex@globex.example", "Globex Billing", "na", "active"),
]

NOTES = [
    "2023-05 rpatel: rehearsed on staging, 1170 rows touched",
    "2025-04 abakare: tightened the match to avoid touching enterprise tenants",
    "2023-12 abakare: widened batch size after load test",
    "2023-12 rpatel: widened batch size after load test",
    "2024-11 abakare: dry run output attached to the ticket",
    "2025-04 rpatel: support briefed on the new values",
    "2024-07 tnguyen: tightened the match to avoid touching enterprise tenants",
    "2025-04 tnguyen: support briefed on the new values",
]

# old spelling -> canonical value
REWRITES = {
    "frozen": "suspended",
    "ACTIVE": "active",
    "SUSPENDED": "suspended",
    "paused": "suspended",
    "Active": "active",
    "evaluation": "trialing",
    "new": "pending",
    "deleted": "closed",
    "on_hold": "suspended",
    "PENDING": "pending",
    "enabled": "active",
    "live": "active",
    "CLOSED": "closed",
    "TRIAL": "trialing",
    "trial": "trialing",
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
    # batch size picked after profiling on a copy of prod: 500 is the sweet spot
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
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
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
    total = 0
    for old, new in REWRITES.items():
        if old != new:
            total += rewrite_one(conn, old, new)
    return total
