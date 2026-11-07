"""Migration 0025: ref uppercase."""

REVISION = "0025"


def upgrade(conn):
    conn.execute("UPDATE invoices SET ref = upper(ref)")
