"""Migration 0022: close paid invoices."""

REVISION = "0022"


def upgrade(conn):
    conn.execute(
        "UPDATE invoices SET status = ? WHERE status = ?",
        ('closed', 'paid'),
    )
