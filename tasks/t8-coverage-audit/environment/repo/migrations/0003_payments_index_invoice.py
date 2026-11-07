"""Migration 0003: payments index invoice."""

REVISION = "0003"


def upgrade(conn):
    conn.execute("CREATE INDEX IF NOT EXISTS ix_payments_invoice ON payments (invoice_id)")
