"""Migration 0032: reindex accounts."""

REVISION = "0032"


def upgrade(conn):
    conn.execute("REINDEX ix_accounts_email")
