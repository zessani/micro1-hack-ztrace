"""Migration 0002: invoices index account."""

REVISION = "0002"


def upgrade(conn):
    conn.execute("CREATE INDEX IF NOT EXISTS ix_invoices_account ON invoices (account_id)")
