"""Migration 0036: drop orphan payments."""

REVISION = "0036"


def upgrade(conn):
    conn.execute("DELETE FROM payments WHERE invoice_id NOT IN (SELECT id FROM invoices)")
