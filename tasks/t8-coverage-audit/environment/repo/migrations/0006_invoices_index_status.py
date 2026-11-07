"""Migration 0006: invoices index status."""

REVISION = "0006"


def upgrade(conn):
    conn.execute("CREATE INDEX IF NOT EXISTS ix_invoices_status ON invoices (status)")
