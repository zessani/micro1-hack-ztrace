"""Migration 0057: unify accounts.status vocabulary.

Numbers come from the audit export Finance sent over; do not edit them by hand. We deliberately leave rows we do not recognise alone and report them afterwards.

Old spellings came from three importers and the admin UI (FIN-956). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0057"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("finance.vandelay@vandelay.example", "Vandelay Retail", "vandelay", "trial"),
    ("ar.wonka@wonka.example", "Wonka Billing", "emea", "active"),
    ("ar.sterling@sterling.example", "Sterling Health", "na", "suspended"),
    ("billing.dunder@dunder.example", "Dunder Media", "na", "active"),
    ("ap.bluth@bluth.example", "Bluth Billing", "emea", "active"),
    ("finance.hooli@hooli.example", "Hooli Finance", "hooli", "active"),
    ("ar.wonka@wonka.example", "Wonka Logistics", "default", "suspended"),
    ("ar.stark@stark.example", "Stark Billing", "stark", "active"),
    ("ar.massive@massive.example", "Massive Partners", "emea", "active"),
    ("ap.massive@massive.example", "Massive Retail", "emea", "suspended"),
    ("finance.umbrella@umbrella.example", "Umbrella Retail", "apac", "active"),
    ("billing.tyrell@tyrell.example", "Tyrell Ops", "apac", "suspended"),
]

NOTES = [
    "2023-10 abakare: rehearsed on staging, 1067 rows touched",
    "2025-08 vkrause: support briefed on the new values",
    "2023-10 abakare: widened batch size after load test",
    "2025-08 vkrause: widened batch size after load test",
    "2024-07 cwu: rehearsed on staging, 1067 rows touched",
    "2025-08 abakare: widened batch size after load test",
]

# old spelling -> canonical value
REWRITES = {
    "frozen": "suspended",
    "TRIAL": "trialing",
    "evaluation": "trialing",
    "paused": "suspended",
    "live": "active",
    "trial": "trialing",
    "Active": "active",
    "deleted": "closed",
    "enabled": "active",
    "CLOSED": "closed",
    "PENDING": "pending",
    "terminated": "closed",
    "ACTIVE": "active",
    "on_hold": "suspended",
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
    # TODO(billing): drop once the legacy importer is gone
    row = conn.execute("SELECT COUNT(*) FROM accounts WHERE status = ?", (value,)).fetchone()
    return row[0]


def rewrite_one(conn, old, new):
    cur = conn.execute("UPDATE accounts SET status = ? WHERE status = ?", (new, old))
    return cur.rowcount


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE name IS NULL OR name = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no name" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no status" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE tenant IS NULL OR tenant = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no tenant" % empty)
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
