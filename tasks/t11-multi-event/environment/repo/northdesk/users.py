def find_by_email(conn, email):
    return conn.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()


def create(conn, email, name, role="agent"):
    if find_by_email(conn, email) is not None:
        raise ValueError(f"email already registered: {email}")
    cur = conn.execute(
        "INSERT INTO users (email, name, role) VALUES (?, ?, ?)",
        (email.lower(), name, role),
    )
    conn.commit()
    return cur.lastrowid


def count(conn):
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
