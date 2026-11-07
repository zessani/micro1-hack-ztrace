import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS legacy_accounts (
    id INTEGER PRIMARY KEY, email TEXT, name TEXT, plan TEXT, created TEXT
);
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    plan TEXT NOT NULL,
    created TEXT
);
"""


def connect(path):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn
