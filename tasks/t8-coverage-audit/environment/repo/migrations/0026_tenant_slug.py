"""Migration 0026: tenant slug."""

REVISION = "0026"


def upgrade(conn):
    conn.execute("UPDATE accounts SET tenant = lower(tenant) WHERE tenant IS NOT NULL")
