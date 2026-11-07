"""Migration 0037: payment method cleanup."""

REVISION = "0037"
ALIASES = {"cc": "card", "bank": "transfer"}


def payments_by_method(conn, method):
    return conn.execute(
        "SELECT id, method FROM payments WHERE method = '{}'".format(method)
    ).fetchall()


def upgrade(conn):
    for old, new in ALIASES.items():
        for row in payments_by_method(conn, old):
            conn.execute("UPDATE payments SET method = ? WHERE id = ?", (new, row[0]))
