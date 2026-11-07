def get(conn, account_id):
    return conn.execute("SELECT id, email, name, tenant FROM accounts WHERE id = ?", (account_id,)).fetchone()


def create(conn, email, name, tenant="default"):
    cur = conn.execute("INSERT INTO accounts (email, name, tenant, status) VALUES (?, ?, ?, 'active')", (email, name, tenant))
    return cur.lastrowid
