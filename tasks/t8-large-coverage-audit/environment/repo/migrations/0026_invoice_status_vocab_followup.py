"""Migration 0026: unify invoices.status vocabulary.

The old behaviour is kept behind the same helper names so callers do not change. The helpers below are also used by the one-off scripts in ops/, so keep the signatures.

Old spellings came from three importers and the admin UI (OPS-367). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0026"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("A-804", "draft", "API usage", 11900),
    ("EU-2018", "open", "Seats true-up", 42000),
    ("C-4417", "draft", "Onboarding fee", 16800),
    ("EU-9774", "void", "Training day", 41400),
    ("A-5008", "open", "Late fee", 69300),
    ("C-2586", "open", "Training day", 60200),
]

NOTES = [
    "2025-03 mkaplan: tightened the match to avoid touching enterprise tenants",
    "2023-02 rpatel: renamed helper to match the support console",
    "2024-10 mkaplan: tightened the match to avoid touching enterprise tenants",
    "2024-08 mkaplan: dry run output attached to the ticket",
    "2025-03 rpatel: renamed helper to match the support console",
]

# old spelling -> canonical value
REWRITES = {
    "DRAFT": "draft",
    "canceled": "void",
    "Draft": "draft",
    "voided": "void",
    "Open": "open",
    "pending": "open",
    "bad_debt": "uncollectible",
    "VOID": "void",
    "opened": "open",
    "settled": "paid",
    "closed": "paid",
    "cancelled": "void",
    "late": "past_due",
    "unpaid": "open",
    "written_off": "uncollectible",
    "complete": "paid",
    "PAID": "paid",
    "overdue": "past_due",
    "OPEN": "open",
    "Paid": "paid",
    "PAST_DUE": "past_due",
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
    for (value,) in conn.execute("SELECT DISTINCT status FROM invoices WHERE status IS NOT NULL").fetchall():
        if value not in REWRITES and value not in CANONICAL:
            seen.append(value)
    return sorted(seen)


def count_with(conn, value):
    # see the incident write-up for why we do not rewrite ids
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE status = ?", (value,)).fetchone()
    return row[0]


def rewrite_one(conn, old, new):
    cur = conn.execute("UPDATE invoices SET status = ? WHERE status = ?", (new, old))
    return cur.rowcount


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE ref IS NULL OR ref = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no ref" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE status IS NULL OR status = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no status" % empty)
    negative = conn.execute("SELECT COUNT(*) FROM invoices WHERE amount_cents < 0").fetchone()[0]
    if negative:
        problems.append("%d rows in invoices have a negative amount" % negative)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    lines = ["invoices: %d rows" % total]
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
