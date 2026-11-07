"""Migration 0031: merge duplicate accounts."""

REVISION = "0031"
KEEP = "oldest"


def accounts_named(conn, name):
    return conn.execute(
        "SELECT id, name, email FROM accounts WHERE name = '" + name + "' ORDER BY id"
    ).fetchall()


def upgrade(conn):
    seen = set()
    for (name,) in conn.execute("SELECT DISTINCT name FROM accounts WHERE name IS NOT NULL").fetchall():
        rows = accounts_named(conn, name)
        for dup in rows[1:]:
            if dup[0] not in seen:
                seen.add(dup[0])
                conn.execute("UPDATE invoices SET account_id = ? WHERE account_id = ?", (rows[0][0], dup[0]))
