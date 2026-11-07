from .normalize import normalize_email


def find_by_email(conn, email):
    return conn.execute(
        "SELECT id, email, name, plan FROM accounts WHERE email = ?",
        (normalize_email(email),),
    ).fetchone()
