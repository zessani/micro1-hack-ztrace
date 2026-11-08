import sqlite3

from custdesk import settings


def load_customers(path=None):
    conn = sqlite3.connect(f"file:{path or settings.database_path()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, name, email FROM customers ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search(customers, term):
    term = term.lower()
    return [c for c in customers if term in c["name"].lower() or term in c["email"].lower()]
