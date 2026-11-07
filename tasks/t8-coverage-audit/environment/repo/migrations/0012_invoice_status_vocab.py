"""Migration 0012: invoice status vocab."""

REVISION = "0012"


def upgrade(conn):
    conn.execute(
        "UPDATE invoices SET status = ? WHERE status = ?",
        ('open', 'pending'),
    )
