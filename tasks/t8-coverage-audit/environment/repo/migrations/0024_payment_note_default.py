"""Migration 0024: payment note default."""

REVISION = "0024"


def upgrade(conn):
    conn.execute(
        "UPDATE payments SET note = ? WHERE note IS NULL",
        ('',),
    )
