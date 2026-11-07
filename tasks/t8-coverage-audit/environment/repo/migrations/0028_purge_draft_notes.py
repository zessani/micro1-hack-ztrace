"""Migration 0028: purge draft notes."""

REVISION = "0028"


def upgrade(conn):
    conn.execute("DELETE FROM notes WHERE body LIKE 'DRAFT:%'")
