"""Migration 0027: cleanup test accounts."""

REVISION = "0027"


def upgrade(conn):
    conn.execute("DELETE FROM accounts WHERE email LIKE '%@test.invalid'")
