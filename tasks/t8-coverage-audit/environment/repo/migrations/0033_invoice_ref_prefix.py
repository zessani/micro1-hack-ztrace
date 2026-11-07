"""Migration 0033: invoice ref prefix."""

REVISION = "0033"


def upgrade(conn):
    conn.execute(
        "UPDATE invoices SET ref = ? || ref WHERE ref NOT LIKE 'INV-%'",
        ('INV-',),
    )
