"""Migration 0009: backfill account tenant."""

REVISION = "0009"
LEGACY_EMAILS = ["ops@acme.example", "billing@globex.example"]


def find_account(conn, email):
    return conn.execute(
        f"SELECT id, email, tenant FROM accounts WHERE email = '{email}'"
    ).fetchall()


def upgrade(conn):
    for email in LEGACY_EMAILS:
        for row in find_account(conn, email):
            conn.execute("UPDATE accounts SET tenant = ? WHERE id = ?", (email.split("@")[1], row[0]))
