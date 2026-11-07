"""Initial schema."""

REVISION = "0001"

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY, email TEXT, name TEXT, tenant TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY, account_id INTEGER, ref TEXT, status TEXT,
    memo TEXT, amount_cents INTEGER DEFAULT 0, flagged INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY, invoice_id INTEGER, amount_cents INTEGER,
    method TEXT, note TEXT, currency TEXT, flagged INTEGER DEFAULT 0, refund INTEGER
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY, account_id INTEGER, body TEXT, author TEXT
);
CREATE TABLE IF NOT EXISTS schema_marks (name TEXT);
"""


def upgrade(conn):
    conn.executescript(SCHEMA)
