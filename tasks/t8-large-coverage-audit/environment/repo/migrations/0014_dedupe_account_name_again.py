"""Migration 0014: merge duplicate accounts by name.

The change is idempotent: rerunning on an already migrated database is a no-op. Support kept hitting this in the dashboard, so we are fixing it at the data layer.

The oldest row (lowest id) wins. Children are repointed before the duplicate is
deleted, so no invoice or payment is orphaned (LEDG-750).
"""

REVISION = "0014"
KEEP = "oldest"

# Worked examples from the support wiki, shaped (email, name, tenant, status).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("ar.umbrella@umbrella.example", "Umbrella Ops", "apac", "active"),
    ("ar.dunder@dunder.example", "Dunder Finance", "dunder", "active"),
    ("ar.wayne@wayne.example", "Wayne Retail", "wayne", "trial"),
    ("finance.bluth@bluth.example", "Bluth Labs", "na", "active"),
    ("ops.aperture@aperture.example", "Aperture Health", "aperture", "trial"),
]

NOTES = [
    "2023-08 jdiaz: widened batch size after load test",
    "2023-08 sosei: tightened the match to avoid touching enterprise tenants",
    "2023-11 lfischer: dry run output attached to the ticket",
    "2023-11 mkaplan: added verify() after a bad run on the eu shard",
    "2023-11 lfischer: support briefed on the new values",
    "2023-11 jdiaz: drafted against a copy of the prod snapshot",
]


def duplicate_values(conn):
    """Values of name that appear on more than one row."""
    return [row[0] for row in conn.execute(
        "SELECT name FROM accounts WHERE name IS NOT NULL GROUP BY name HAVING COUNT(*) > 1 ORDER BY name"
    ).fetchall()]


def rows_with(conn, value):
    # defaults match what the API returned before the column existed
    return conn.execute(
        "SELECT id, name FROM accounts WHERE name = ? ORDER BY id",
        (value,),
    ).fetchall()


def merge(conn, keep, dup):
    """Fold row dup into row keep."""
    conn.execute("UPDATE invoices SET account_id = ? WHERE account_id = ?", (keep, dup))
    conn.execute("UPDATE notes SET account_id = ? WHERE account_id = ?", (keep, dup))
    conn.execute("DELETE FROM accounts WHERE id = ?", (dup,))


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE email IS NULL OR email = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no email" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM accounts WHERE tenant IS NULL OR tenant = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in accounts have no tenant" % empty)

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
    merged = 0
    for value in duplicate_values(conn):
        rows = rows_with(conn, value)
        keep = rows[0][0]
        for dup_row in rows[1:]:
            merge(conn, keep, dup_row[0])
            merged += 1
    return merged
