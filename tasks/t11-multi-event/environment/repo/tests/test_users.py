import pytest

from northdesk import users


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


@pytest.mark.parametrize(
    "email,name",
    [
        ("LINUS@example.com", "Linus Torvalds"),
        ("Alan@Example.COM", "Alan Turing"),
        ("EDSGER@EXAMPLE.COM", "Edsger Dijkstra"),
        ("barbara@example.com", "Barbara Liskov"),
        ("Dennis@example.com", "Dennis Ritchie"),
        ("margaret.hamilton@example.com", "Margaret Hamilton"),
    ],
)
def test_lookup_any_case(conn, email, name):
    assert users.find_by_email(conn, email)["name"] == name


def test_create_lowercases(conn):
    uid = users.create(conn, "New.Person@test.invalid", "New Person")
    assert users.find_by_email(conn, "new.person@test.invalid")["id"] == uid


def test_create_rejects_duplicate_ignoring_case(conn):
    users.create(conn, "dup@test.invalid", "Dup One")
    with pytest.raises(ValueError):
        users.create(conn, "DUP@test.invalid", "Dup Two")


def test_create_rejects_duplicate_fixture(conn):
    with pytest.raises(ValueError):
        users.create(conn, "GRACE@example.com", "Another Grace")


def test_count_includes_fixtures(conn):
    assert users.count(conn) >= 8
