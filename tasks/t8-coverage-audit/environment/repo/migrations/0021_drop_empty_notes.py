"""Migration 0021: drop empty notes."""

REVISION = "0021"


def upgrade(conn):
    conn.execute(
        "DELETE FROM notes WHERE body = ?",
        ('',),
    )
