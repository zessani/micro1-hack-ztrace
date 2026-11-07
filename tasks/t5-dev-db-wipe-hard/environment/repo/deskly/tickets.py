def open_for_user(conn, user_id):
    return conn.execute(
        "SELECT * FROM tickets WHERE user_id = ? AND status = 'open' ORDER BY id",
        (user_id,),
    ).fetchall()


def add(conn, user_id, subject):
    cur = conn.execute(
        "INSERT INTO tickets (user_id, subject) VALUES (?, ?)", (user_id, subject)
    )
    conn.commit()
    return cur.lastrowid


def close(conn, ticket_id):
    conn.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
    conn.commit()
