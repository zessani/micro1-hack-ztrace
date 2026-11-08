def open_for_user(conn, user_id):
    return conn.execute(
        "SELECT * FROM tickets WHERE user_id = ? AND status = 'open' ORDER BY id",
        (user_id,),
    ).fetchall()


def add(conn, user_id, subject):
    subject = subject.strip()
    if not subject:
        raise ValueError("subject must not be blank")
    cur = conn.execute(
        "INSERT INTO tickets (user_id, subject) VALUES (?, ?)", (user_id, subject)
    )
    conn.commit()
    return cur.lastrowid


def close(conn, ticket_id):
    cur = conn.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
    if cur.rowcount == 0:
        raise KeyError(ticket_id)
    conn.commit()
