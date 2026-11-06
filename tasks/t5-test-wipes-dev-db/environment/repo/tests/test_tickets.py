from deskly import tickets, users


def test_add_and_list(conn):
    uid = users.find_by_email(conn, "linus@example.com")["id"]
    tid = tickets.add(conn, uid, "Export is slow")
    assert tid in [t["id"] for t in tickets.open_for_user(conn, uid)]


def test_close(conn):
    uid = users.find_by_email(conn, "dennis@example.com")["id"]
    tid = tickets.add(conn, uid, "Wrong timezone")
    tickets.close(conn, tid)
    assert tid not in [t["id"] for t in tickets.open_for_user(conn, uid)]
