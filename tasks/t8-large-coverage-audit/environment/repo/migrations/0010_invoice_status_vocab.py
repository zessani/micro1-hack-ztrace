"""Migration 0010: unify invoices.status vocabulary.

Staging showed roughly a third of rows needed the fix; production should be similar. If the lookup returns nothing we fall through to the default instead of raising.

Old spellings came from three importers and the admin UI (FIN-479). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0010"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("INV-1403", "draft", "Hosting", 12200),
    ("INV-3867", "draft", "Implementation", 50700),
    ("C-3483", "open", "Training day", 55900),
    ("EU-5016", "draft", "Annual licence", 82000),
    ("C-1055", "open", "March services", 63300),
    ("B-6279", "void", "Support retainer", 14300),
]

NOTES = [
    "2024-01 mkaplan: tightened the match to avoid touching enterprise tenants",
    "2024-11 cwu: added verify() after a bad run on the eu shard",
    "2024-11 vkrause: widened batch size after load test",
    "2023-03 mkaplan: rehearsed on staging, 5922 rows touched",
    "2025-09 cwu: reviewed by billing ops",
    "2024-11 mkaplan: rollback plan written (restore from nightly dump)",
]

# old spelling -> canonical value
REWRITES = {
    "PAID": "paid",
    "bad_debt": "uncollectible",
    "unpaid": "open",
    "settled": "paid",
    "opened": "open",
    "overdue": "past_due",
    "pending": "open",
    "PAST_DUE": "past_due",
    "Paid": "paid",
    "voided": "void",
    "Draft": "draft",
    "Open": "open",
    "complete": "paid",
    "DRAFT": "draft",
    "cancelled": "void",
    "canceled": "void",
    "VOID": "void",
    "OPEN": "open",
    "closed": "paid",
    "late": "past_due",
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
    # the order of this list is significant; first match wins
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
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE memo IS NULL OR memo = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no memo" % empty)
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
