"""Migration 0027: unify payments.method vocabulary.

This runs before the nightly export, which assumes the cleaned-up values. The helpers below are also used by the one-off scripts in ops/, so keep the signatures.

Old spellings came from three importers and the admin UI (SUP-201). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0027"

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("upi", 3825, "CHF", "reconciled"),
    ("pix", 9300, "CHF", "reconciled"),
    ("sepa", 8625, "EUR", "partial"),
    ("wire", 7900, "NZD", "second instalment"),
    ("credit", 8225, "CHF", "bank ref pending"),
    ("cash", 4100, "USD", ""),
]

NOTES = [
    "2023-06 vkrause: drafted against a copy of the prod snapshot",
    "2023-11 lfischer: added verify() after a bad run on the eu shard",
    "2024-11 lfischer: dry run output attached to the ticket",
    "2023-06 rpatel: rollback plan written (restore from nightly dump)",
]

# old spelling -> canonical value
REWRITES = {
    "ACH": "ach",
    "bank_transfer": "wire",
    "cc": "card",
    "cash_on_hand": "cash",
    "pp": "paypal",
    "SWIFT": "wire",
    "cheque": "check",
    "mastercard": "card",
    "CC": "card",
    "debit": "card",
    "Visa": "card",
    "bank": "wire",
    "credit_card": "card",
    "direct_debit": "ach",
    "amex": "card",
}

CANONICAL = sorted(set(REWRITES.values()))


def canonical(value):
    """Map any known spelling to the canonical one; unknown values pass through."""
    if value is None:
        return None
    return REWRITES.get(value, value)


def unknown_values(conn):
    """Distinct method values that are neither canonical nor rewritable."""
    seen = []
    for (value,) in conn.execute("SELECT DISTINCT method FROM payments WHERE method IS NOT NULL").fetchall():
        if value not in REWRITES and value not in CANONICAL:
            seen.append(value)
    return sorted(seen)


def count_with(conn, value):
    # we count what we changed so the runner can log it
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE method = ?", (value,)).fetchone()
    return row[0]


def rewrite_one(conn, old, new):
    cur = conn.execute("UPDATE payments SET method = ? WHERE method = ?", (new, old))
    return cur.rowcount


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE method IS NULL OR method = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no method" % empty)
    negative = conn.execute("SELECT COUNT(*) FROM payments WHERE amount_cents < 0").fetchone()[0]
    if negative:
        problems.append("%d rows in payments have a negative amount" % negative)

    return problems


def summary(conn):
    """One line per check, used when the migration is run by hand."""
    total = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    lines = ["payments: %d rows" % total]
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
