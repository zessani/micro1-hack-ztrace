from deskly import users


def test_find_exact_email(conn):
    assert users.find_by_email(conn, "grace@example.com")["name"] == "Grace Hopper"


def test_find_mixed_case_email(conn):
    row = users.find_by_email(conn, "Grace@Example.com")
    assert row is not None and row["name"] == "Grace Hopper"


def test_find_stored_mixed_case(conn):
    row = users.find_by_email(conn, "ada.lovelace@example.com")
    assert row is not None and row["name"] == "Ada Lovelace"


def test_find_missing(conn):
    assert users.find_by_email(conn, "nobody@example.com") is None


def test_create_lowercases(conn):
    uid = users.create(conn, "New.Person@Example.com", "New Person")
    assert users.find_by_email(conn, "new.person@example.com")["id"] == uid
