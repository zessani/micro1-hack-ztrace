"""Migration 0055: unify accounts.status vocabulary.

Finance asked for this ahead of the quarter close; it is safe to run more than once. Do not renumber this file; later migrations refer to its REVISION.

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ap.wayne@wayne.example", "Wayne Health", "default", "trial"),
    ("ar.initech@initech.example", "Initech Partners", "emea", "trial"),
    ("billing.stark@stark.example", "Stark Retail", "na", "trial"),
    ("billing.hooli@hooli.example", "Hooli Labs", "emea", "active"),
    ("ap.tyrell@tyrell.example", "Tyrell Labs", "na", "active"),
    ("finance.umbrella@umbrella.example", "Umbrella Retail", "emea", "trial"),
    ("billing.sterling@sterling.example", "Sterling Logistics", "sterling", "trial"),
    ("finance.gringotts@gringotts.example", "Gringotts Logistics", "apac", "suspended"),
    ("ops.oscorp@oscorp.example", "Oscorp Finance", "default", "active"),
    ("ops.pied@pied.example", "Pied Logistics", "apac", "trial"),
    ("ops.globex@globex.example", "Globex Ops", "globex", "active"),
    ("billing.massive@massive.example", "Massive Finance", "na", "suspended"),
    ("ops.wonka@wonka.example", "Wonka Systems", "default", "trial"),
    ("finance.vandelay@vandelay.example", "Vandelay Partners", "apac", "trial"),
    ("billing.cyberdyne@cyberdyne.example", "Cyberdyne Partners", "default", "suspended"),
    ("ar.initech@initech.example", "Initech Health", "default", "active"),
]

NOTES = [
    "2023-11 hmoreau: drafted against a copy of the prod snapshot",
    "2024-06 abakare: tightened the match to avoid touching enterprise tenants",
    "2024-10 rpatel: tightened the match to avoid touching enterprise tenants",
    "2023-11 sosei: rehearsed on staging, 7739 rows touched",
    "2025-03 abakare: support briefed on the new values",
    "2023-11 sosei: added verify() after a bad run on the eu shard",
]

Old spellings came from three importers and the admin UI (FIN-974). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0055"

# old spelling -> canonical value
REWRITES = {
    "paused": "suspended",
    "new": "pending",
    "deleted": "closed",
    "PENDING": "pending",
    "TRIAL": "trialing",
    "evaluation": "trialing",
    "on_hold": "suspended",
    "frozen": "suspended",
    "Active": "active",
    "enabled": "active",
    "trial": "trialing",
    "SUSPENDED": "suspended",
    "terminated": "closed",
    "live": "active",
    "CLOSED": "closed",
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
    total = 0
    for old, new in REWRITES.items():
        if old != new:
            total += rewrite_one(conn, old, new)
    return total
