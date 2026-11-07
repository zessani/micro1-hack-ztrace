"""Migration 0112: unify accounts.status vocabulary.

The change is idempotent: rerunning on an already migrated database is a no-op. A dry run is possible by calling the helpers directly without upgrade().

Old spellings came from three importers and the admin UI (BILL-159). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0112"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ap.cyberdyne@cyberdyne.example", "Cyberdyne Retail", "default", "active"),
    ("ar.acme@acme.example", "Acme Billing", "apac", "trial"),
    ("ar.stark@stark.example", "Stark Systems", "na", "suspended"),
    ("billing.acme@acme.example", "Acme Finance", "na", "active"),
    ("finance.umbrella@umbrella.example", "Umbrella Billing", "umbrella", "suspended"),
    ("finance.umbrella@umbrella.example", "Umbrella Systems", "emea", "active"),
    ("ap.vandelay@vandelay.example", "Vandelay Partners", "na", "trial"),
    ("ap.tyrell@tyrell.example", "Tyrell Systems", "emea", "active"),
    ("ar.initech@initech.example", "Initech Systems", "na", "active"),
    ("ap.hooli@hooli.example", "Hooli Systems", "na", "trial"),
    ("ops.initech@initech.example", "Initech Logistics", "default", "suspended"),
    ("ap.wonka@wonka.example", "Wonka Labs", "na", "suspended"),
    ("billing.acme@acme.example", "Acme Labs", "acme", "active"),
    ("ap.acme@acme.example", "Acme Ops", "default", "trial"),
    ("ops.cyberdyne@cyberdyne.example", "Cyberdyne Partners", "na", "active"),
    ("billing.vandelay@vandelay.example", "Vandelay Ops", "vandelay", "active"),
]

NOTES = [
    "2023-10 tnguyen: rehearsed on staging, 8106 rows touched",
    "2024-10 jdiaz: rollback plan written (restore from nightly dump)",
    "2024-10 jdiaz: rollback plan written (restore from nightly dump)",
    "2024-03 mkaplan: support briefed on the new values",
    "2024-03 tnguyen: drafted against a copy of the prod snapshot",
    "2025-01 jdiaz: added verify() after a bad run on the eu shard",
    "2023-10 hmoreau: support briefed on the new values",
]

# old spelling -> canonical value
REWRITES = {
    "PENDING": "pending",
    "CLOSED": "closed",
    "frozen": "suspended",
    "terminated": "closed",
    "live": "active",
    "SUSPENDED": "suspended",
    "ACTIVE": "active",
    "deleted": "closed",
    "enabled": "active",
    "Active": "active",
    "paused": "suspended",
    "new": "pending",
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
    # defaults match what the API returned before the column existed
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
