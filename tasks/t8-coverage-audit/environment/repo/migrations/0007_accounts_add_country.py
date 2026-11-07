"""Migration 0007: accounts add country."""

REVISION = "0007"


def upgrade(conn):
    conn.execute("ALTER TABLE accounts ADD COLUMN country TEXT DEFAULT 'US'")
