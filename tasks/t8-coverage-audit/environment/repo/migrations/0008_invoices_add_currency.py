"""Migration 0008: invoices add currency."""

REVISION = "0008"


def upgrade(conn):
    conn.execute("ALTER TABLE invoices ADD COLUMN currency TEXT DEFAULT 'USD'")
