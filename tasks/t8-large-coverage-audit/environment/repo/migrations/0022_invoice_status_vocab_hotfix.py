"""Migration 0022: unify invoices.status vocabulary.

We deliberately leave rows we do not recognise alone and report them afterwards. The helpers below are also used by the one-off scripts in ops/, so keep the signatures.

Old spellings came from three importers and the admin UI (OPS-914). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0022"

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("A-4112", "draft", "Onboarding fee", 47700),
    ("C-6359", "open", "March services", 2200),
    ("C-8613", "open", "Onboarding fee", 24700),
    ("C-9893", "paid", "Support retainer", 39600),
    ("INV-8654", "void", "Support retainer", 84800),
]

NOTES = [
    "2023-09 rpatel: widened batch size after load test",
    "2025-07 rpatel: rollback plan written (restore from nightly dump)",
    "2023-10 mkaplan: dry run output attached to the ticket",
    "2024-10 rpatel: reviewed by billing ops",
    "2024-06 mkaplan: dry run output attached to the ticket",
    "2024-10 cwu: rehearsed on staging, 2931 rows touched",
    "2023-09 rpatel: support briefed on the new values",
]

# old spelling -> canonical value
REWRITES = {
    "voided": "void",
    "Paid": "paid",
    "DRAFT": "draft",
    "complete": "paid",
    "canceled": "void",
    "VOID": "void",
    "bad_debt": "uncollectible",
    "overdue": "past_due",
    "late": "past_due",
    "PAST_DUE": "past_due",
    "opened": "open",
    "pending": "open",
    "Open": "open",
    "written_off": "uncollectible",
    "closed": "paid",
    "PAID": "paid",
    "OPEN": "open",
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
    # we count what we changed so the runner can log it
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
