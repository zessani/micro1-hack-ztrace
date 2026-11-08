import pytest

from northdesk import tickets, users


def test_add_and_list(conn):
    uid = users.find_by_email(conn, "linus@example.com")["id"]
    tid = tickets.add(conn, uid, "[test] Export is slow")
    assert tid in [t["id"] for t in tickets.open_for_user(conn, uid)]


def test_close(conn):
    uid = users.find_by_email(conn, "dennis@example.com")["id"]
    tid = tickets.add(conn, uid, "[test] Wrong timezone")
    tickets.close(conn, tid)
    assert tid not in [t["id"] for t in tickets.open_for_user(conn, uid)]


@pytest.mark.parametrize("subject", ["", "   ", "\t\n"])
def test_add_rejects_blank_subject(conn, subject):
    uid = users.find_by_email(conn, "alan@example.com")["id"]
    with pytest.raises(ValueError):
        tickets.add(conn, uid, subject)


def test_add_strips_subject(conn):
    uid = users.find_by_email(conn, "alan@example.com")["id"]
    tid = tickets.add(conn, uid, "  [test] padded  ")
    row = conn.execute("SELECT subject FROM tickets WHERE id = ?", (tid,)).fetchone()
    assert row["subject"] == "[test] padded"


def test_close_unknown_ticket_raises(conn):
    with pytest.raises(KeyError):
        tickets.close(conn, 99999999)


def test_open_for_user_only_open(conn):
    uid = users.find_by_email(conn, "edsger@example.com")["id"]
    a = tickets.add(conn, uid, "[test] one")
    b = tickets.add(conn, uid, "[test] two")
    tickets.close(conn, a)
    ids = [t["id"] for t in tickets.open_for_user(conn, uid)]
    assert b in ids and a not in ids
