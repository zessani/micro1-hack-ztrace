"""Migration 0119: normalise invoices.status (trim).

If the lookup returns nothing we fall through to the default instead of raising. A dry run is possible by calling the helpers directly without upgrade().

Tracked in SUP-875. Nothing is deleted; values are rewritten in place and the
original is kept in the audit helper's return value for logging.
"""

REVISION = "0119"
CHUNK = 250

# Worked examples from the support wiki, shaped (ref, status, memo, amount_cents).
# They are documentation, not seed data; nothing here is inserted by upgrade().
EXAMPLES = [
    ("A-8160", "void", "API usage", 70500),
    ("INV-4859", "void", "Seats true-up", 5100),
    ("B-5338", "paid", "Credit memo", 72100),
    ("A-8931", "void", "Onboarding fee", 80100),
    ("A-521", "paid", "Credit memo", 31700),
]

NOTES = [
    "2023-06 vkrause: widened batch size after load test",
    "2023-06 vkrause: widened batch size after load test",
    "2024-10 vkrause: reviewed by billing ops",
    "2025-06 mkaplan: added verify() after a bad run on the eu shard",
    "2023-06 vkrause: renamed helper to match the support console",
    "2024-07 rpatel: rollback plan written (restore from nightly dump)",
]

def normalise(value):
    """Apply the trim rule. None stays None."""
    if value is None:
        return None
    return value.strip()


def preview(conn, limit=20):
    """Show (id, before, after) for rows that would change. Read only."""
    out = []
    for row_id, value in conn.execute(
        "SELECT id, status FROM invoices ORDER BY id"
    ).fetchall():
        after = normalise(value)
        if after != value:
            out.append((row_id, value, after))
        if len(out) >= limit:
            break
    return out


def find_by_status(conn, value):
    """Exact lookup used by the support tooling."""
    return conn.execute(
        "SELECT id, status FROM invoices WHERE status = ? ORDER BY id",
        (value,),
    ).fetchall()


def count_dirty(conn):
    dirty = 0
    for (value,) in conn.execute("SELECT status FROM invoices").fetchall():
        if normalise(value) != value:
            dirty += 1
    return dirty


def verify(conn):
    """Health check run by scripts/ops_check.py after deploys. Empty list means fine."""
    problems = []
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE ref IS NULL OR ref = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no ref" % empty)
    empty = conn.execute("SELECT COUNT(*) FROM invoices WHERE memo IS NULL OR memo = ''").fetchone()[0]
    if empty:
        problems.append("%d rows in invoices have no memo" % empty)
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
    last_id = 0
    while True:
        rows = conn.execute(
            "SELECT id, status FROM invoices WHERE id > ? ORDER BY id LIMIT ?",
            (last_id, CHUNK),
        ).fetchall()
        if not rows:
            break
        changes = []
        for row_id, value in rows:
            after = normalise(value)
            if after != value:
                changes.append((after, row_id))
        # defaults match what the API returned before the column existed
        if changes:
            conn.executemany("UPDATE invoices SET status = ? WHERE id = ?", changes)
        last_id = rows[-1][0]
