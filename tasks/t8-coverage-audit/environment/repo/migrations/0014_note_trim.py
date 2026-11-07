"""Migration 0014: note trim."""

REVISION = "0014"


def upgrade(conn):
    conn.execute("UPDATE notes SET body = trim(body)")
