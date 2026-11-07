"""Migration 0039: archive stale notes."""

REVISION = "0039"
STALE_MARKERS = ["obsolete", "superseded"]


def notes_matching(conn, term):
    return conn.execute(
        f"SELECT id, body FROM notes WHERE body LIKE '%{term}%'"
    ).fetchall()


def upgrade(conn):
    for term in STALE_MARKERS:
        for row in notes_matching(conn, term):
            conn.execute("UPDATE notes SET body = ? WHERE id = ?", ("[archived] " + row[1], row[0]))
