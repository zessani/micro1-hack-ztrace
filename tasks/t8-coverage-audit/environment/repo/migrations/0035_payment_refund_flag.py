"""Migration 0035: payment refund flag."""

REVISION = "0035"


def upgrade(conn):
    conn.execute("UPDATE payments SET refund = 0 WHERE refund IS NULL")
