def create(conn, account_id, ref, amount_cents):
    cur = conn.execute(
        "INSERT INTO invoices (account_id, ref, status, amount_cents) VALUES (?, ?, 'open', ?)",
        (account_id, ref, amount_cents),
    )
    return cur.lastrowid


def total_open(conn, account_id):
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) FROM invoices WHERE account_id = ? AND status = 'open'",
        (account_id,),
    ).fetchone()
    return row[0]
