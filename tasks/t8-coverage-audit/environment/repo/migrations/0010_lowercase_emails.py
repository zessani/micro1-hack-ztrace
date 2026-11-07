"""Migration 0010: lowercase emails."""

REVISION = "0010"


def upgrade(conn):
    conn.execute("UPDATE accounts SET email = lower(trim(email)) WHERE email IS NOT NULL")
