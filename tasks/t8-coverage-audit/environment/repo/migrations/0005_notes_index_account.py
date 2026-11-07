"""Migration 0005: notes index account."""

REVISION = "0005"


def upgrade(conn):
    conn.execute("CREATE INDEX IF NOT EXISTS ix_notes_account ON notes (account_id)")
