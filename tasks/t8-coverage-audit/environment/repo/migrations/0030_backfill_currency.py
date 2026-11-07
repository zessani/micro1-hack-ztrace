"""Migration 0030: backfill currency."""

REVISION = "0030"


def upgrade(conn):
    conn.execute(
        "UPDATE invoices SET currency = ? WHERE currency IS NULL",
        ('USD',),
    )
