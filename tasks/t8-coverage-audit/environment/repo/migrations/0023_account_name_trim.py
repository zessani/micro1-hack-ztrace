"""Migration 0023: account name trim."""

REVISION = "0023"


def upgrade(conn):
    conn.execute("UPDATE accounts SET name = trim(name)")
