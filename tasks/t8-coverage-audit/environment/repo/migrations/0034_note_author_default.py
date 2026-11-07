"""Migration 0034: note author default."""

REVISION = "0034"


def upgrade(conn):
    conn.execute(
        "UPDATE notes SET author = ? WHERE author IS NULL",
        ('system',),
    )
