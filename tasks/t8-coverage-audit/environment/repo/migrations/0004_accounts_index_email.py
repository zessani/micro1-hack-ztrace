"""Migration 0004: accounts index email."""

REVISION = "0004"


def upgrade(conn):
    conn.execute("CREATE INDEX IF NOT EXISTS ix_accounts_email ON accounts (email)")
