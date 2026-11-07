"""Migration 0108: unify payments.method vocabulary.

This runs before the nightly export, which assumes the cleaned-up values. We deliberately leave rows we do not recognise alone and report them afterwards.

Old spellings came from three importers and the admin UI (SUP-534). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0108"

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("eft", 8750, "SEK", "bank ref pending"),
    ("manual", 600, "SEK", "reconciled"),
    ("pix", 1450, "SEK", ""),
    ("bacs", 7125, "CAD", "second instalment"),
    ("upi", 6225, "NZD", "bank ref pending"),
    ("ach", 3275, "SEK", "partial"),
    ("ach", 4800, "CHF", "bank ref pending"),
    ("wire", 3150, "AUD", "partial"),
    ("eft", 5300, "AUD", "partial"),
    ("sepa", 7775, "EUR", "second instalment"),
]

NOTES = [
    "2023-07 abakare: reviewed by billing ops",
    "2025-08 sosei: dry run output attached to the ticket",
    "2025-08 hmoreau: support briefed on the new values",
    "2023-07 rpatel: support briefed on the new values",
]

# old spelling -> canonical value
REWRITES = {
    "cc": "card",
    "Check": "check",
    "direct_debit": "ach",
    "Visa": "card",
    "cheque": "check",
    "mastercard": "card",
    "amex": "card",
    "cash_on_hand": "cash",
    "SWIFT": "wire",
    "credit_card": "card",
    "ACH": "ach",
    "bank": "wire",
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
    # see the incident write-up for why we do not rewrite ids
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE method = ?", (value,)).fetchone()
    return row[0]


def rewrite_one(conn, old, new):
    cur = conn.execute("UPDATE payments SET method = ? WHERE method = ?", (new, old))
    return cur.rowcount


def payments_by_method(conn, method):
    """All payments made with one method, oldest first."""
    sql = (
        "SELECT id, method, amount_cents FROM payments "
        "WHERE method = '" + method + "' "
        "ORDER BY id"
    )
    return conn.execute(sql).fetchall()


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE note IS NULL OR note = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no note" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE currency IS NULL OR currency = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no currency" % empty)
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
