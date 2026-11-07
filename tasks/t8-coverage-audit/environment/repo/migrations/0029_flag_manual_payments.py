"""Migration 0029: flag manual payments."""

REVISION = "0029"


def upgrade(conn):
    conn.execute(
        "UPDATE payments SET flagged = 1 WHERE method = ?",
        ('manual',),
    )
