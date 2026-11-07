"""Migration 0020: flag large invoices."""

REVISION = "0020"


def upgrade(conn):
    conn.execute(
        "UPDATE invoices SET flagged = 1 WHERE amount_cents > ?",
        (100000,),
    )
