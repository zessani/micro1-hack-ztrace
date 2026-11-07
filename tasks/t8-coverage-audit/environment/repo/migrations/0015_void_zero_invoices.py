"""Migration 0015: void zero invoices."""

REVISION = "0015"


def upgrade(conn):
    conn.execute(
        "UPDATE invoices SET status = ? WHERE amount_cents = ?",
        ('void', 0),
    )
