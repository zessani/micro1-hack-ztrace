def find_by_email(conn, email):
    return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def create(conn, email, name, role="agent"):
    cur = conn.execute(
        "INSERT INTO users (email, name, role) VALUES (?, ?, ?)",
        (email.lower(), name, role),
    )
    conn.commit()
    return cur.lastrowid


def count(conn):
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
