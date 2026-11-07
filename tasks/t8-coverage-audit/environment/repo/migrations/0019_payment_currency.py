"""Migration 0019: payment currency."""

REVISION = "0019"


def upgrade(conn):
    conn.execute(
        "UPDATE payments SET currency = ? WHERE currency IS NULL",
        ('USD',),
    )
