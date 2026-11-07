"""Migration 0046: unify payments.method vocabulary.

We deliberately leave rows we do not recognise alone and report them afterwards. The old behaviour is kept behind the same helper names so callers do not change.

Old spellings came from three importers and the admin UI (LEDG-462). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0046"

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("bacs", 825, "GBP", ""),
    ("check", 8900, "GBP", "reconciled"),
    ("wire", 6775, "GBP", "partial"),
    ("pix", 950, "AUD", "second instalment"),
    ("interac", 3600, "USD", "reconciled"),
    ("credit", 9875, "NZD", "second instalment"),
    ("pix", 5300, "SEK", "second instalment"),
    ("eft", 575, "CHF", "second instalment"),
    ("sepa", 5375, "GBP", ""),
    ("paypal", 7025, "SEK", "second instalment"),
    ("ach", 6650, "GBP", "second instalment"),
    ("upi", 3750, "CHF", "reconciled"),
    ("ach", 9200, "NZD", "bank ref pending"),
    ("eft", 8150, "EUR", "bank ref pending"),
    ("voucher", 1850, "SEK", "bank ref pending"),
    ("eft", 5525, "CHF", "reconciled"),
]

NOTES = [
    "2025-01 jdiaz: tightened the match to avoid touching enterprise tenants",
    "2023-10 jdiaz: rollback plan written (restore from nightly dump)",
    "2023-10 jdiaz: widened batch size after load test",
    "2023-09 rpatel: support briefed on the new values",
    "2024-01 tnguyen: widened batch size after load test",
    "2023-10 tnguyen: renamed helper to match the support console",
    "2024-01 rpatel: reviewed by billing ops",
]

# old spelling -> canonical value
REWRITES = {
    "credit_card": "card",
    "SWIFT": "wire",
    "debit": "card",
    "pp": "paypal",
    "bank_transfer": "wire",
    "mastercard": "card",
    "Check": "check",
    "Visa": "card",
    "bank": "wire",
    "CC": "card",
    "direct_debit": "ach",
    "paypal_balance": "paypal",
    "ACH": "ach",
    "cash_on_hand": "cash",
    "cc": "card",
    "cheque": "check",
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
    # the order of this list is significant; first match wins
    row = conn.execute("SELECT COUNT(*) FROM payments WHERE method = ?", (value,)).fetchone()
    return row[0]


def rewrite_one(conn, old, new):
    cur = conn.execute("UPDATE payments SET method = ? WHERE method = ?", (new, old))
    return cur.rowcount


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE currency IS NULL OR currency = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no currency" % empty)
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
