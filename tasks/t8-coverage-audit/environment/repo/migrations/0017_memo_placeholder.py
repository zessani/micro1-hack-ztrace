"""Migration 0017: memo placeholder."""

REVISION = "0017"


def upgrade(conn):
    conn.execute(
        "UPDATE invoices SET memo = ? WHERE memo IS NULL",
        ('',),
    )
