import sqlite3


def open_snapshot(path="data/messages.db"):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_messages(path="data/messages.db"):
    conn = open_snapshot(path)
    rows = conn.execute(
        "SELECT id, thread_id, sender, sent_at, body FROM messages ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
