"""Migration 0011: default tenant."""

REVISION = "0011"


def upgrade(conn):
    conn.execute(
        "UPDATE accounts SET tenant = ? WHERE tenant IS NULL",
        ('default',),
    )
