"""Migration 0016: country codes."""

REVISION = "0016"


def upgrade(conn):
    conn.execute(
        "UPDATE accounts SET country = ? WHERE country = ?",
        ('GB', 'UK'),
    )
