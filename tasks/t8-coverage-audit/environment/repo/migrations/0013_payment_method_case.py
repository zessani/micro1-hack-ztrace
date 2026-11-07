"""Migration 0013: payment method case."""

REVISION = "0013"


def upgrade(conn):
    conn.execute("UPDATE payments SET method = lower(method)")
