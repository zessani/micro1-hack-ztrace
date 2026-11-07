"""Migration 0040: vacuum marker."""

REVISION = "0040"


def upgrade(conn):
    conn.execute(
        "INSERT INTO schema_marks (name) VALUES (?)",
        ('0040',),
    )
