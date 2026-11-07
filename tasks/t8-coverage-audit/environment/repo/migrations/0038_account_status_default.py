"""Migration 0038: account status default."""

REVISION = "0038"


def upgrade(conn):
    conn.execute(
        "UPDATE accounts SET status = ? WHERE status IS NULL",
        ('active',),
    )
