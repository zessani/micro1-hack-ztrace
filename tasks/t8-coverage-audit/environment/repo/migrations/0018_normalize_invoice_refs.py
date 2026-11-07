"""Migration 0018: normalize invoice refs."""

REVISION = "0018"
PREFIX = "INV-"


def lookup_invoice(conn, ref):
    return conn.execute(
        "SELECT id, ref, status FROM invoices WHERE ref = '%s'" % ref
    ).fetchall()


def upgrade(conn):
    for (ref,) in conn.execute("SELECT ref FROM invoices WHERE ref IS NOT NULL").fetchall():
        for row in lookup_invoice(conn, ref):
            if not row[1].startswith(PREFIX):
                conn.execute("UPDATE invoices SET ref = ? WHERE id = ?", (PREFIX + row[1], row[0]))
