"""Migration 0098: unify payments.method vocabulary.

The helpers below are also used by the one-off scripts in ops/, so keep the signatures. We deliberately leave rows we do not recognise alone and report them afterwards.

Old spellings came from three importers and the admin UI (SUP-773). We rewrite
them to the canonical lower-case form used by the API.
"""

REVISION = "0098"

# Worked examples from the support wiki, shaped (method, amount_cents, currency, note).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ach", 6025, "USD", "partial"),
    ("sepa", 2875, "AUD", "second instalment"),
    ("card", 6125, "NZD", ""),
    ("card", 1400, "AUD", ""),
    ("ach", 4750, "AUD", "second instalment"),
    ("bacs", 3275, "GBP", ""),
    ("cash", 3375, "AUD", ""),
    ("wire", 6550, "GBP", ""),
    ("sepa", 8800, "CHF", "second instalment"),
    ("paypal", 9625, "USD", "second instalment"),
    ("card", 650, "EUR", ""),
    ("check", 3000, "NZD", "reconciled"),
    ("credit", 8425, "SEK", "reconciled"),
    ("sepa", 8575, "GBP", "bank ref pending"),
    ("wire", 8850, "CHF", "second instalment"),
    ("card", 9125, "CHF", "reconciled"),
]

NOTES = [
    "2024-06 hmoreau: renamed helper to match the support console",
    "2023-11 cwu: support briefed on the new values",
    "2024-06 hmoreau: rehearsed on staging, 2301 rows touched",
    "2024-06 hmoreau: rollback plan written (restore from nightly dump)",
    "2024-10 hmoreau: added verify() after a bad run on the eu shard",
    "2025-09 abakare: added verify() after a bad run on the eu shard",
]

# old spelling -> canonical value
REWRITES = {
    "cc": "card",
    "bank": "wire",
    "Visa": "card",
    "Check": "check",
    "bank_transfer": "wire",
    "direct_debit": "ach",
    "ACH": "ach",
    "mastercard": "card",
    "pp": "paypal",
    "paypal_balance": "paypal",
    "cash_on_hand": "cash",
    "amex": "card",
    "cheque": "check",
    "SWIFT": "wire",
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
    # TODO(billing): drop once the legacy importer is gone
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
    empty = conn.execute("SELECT COUNT(*) FROM payments WHERE note IS NULL OR note = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in payments have no note" % empty)
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
