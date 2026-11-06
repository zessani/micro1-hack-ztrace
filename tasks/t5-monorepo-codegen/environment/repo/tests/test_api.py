from packages.api.handlers import get_user, list_users, make_user, paginate

USERS = [make_user(i, f"user{i}", f"user{i}@acme.test") for i in range(1, 6)]


def test_first_page_lists_first_users():
    assert list_users(USERS, page=1, per_page=2) == ["user1", "user2"]


def test_second_page():
    assert list_users(USERS, page=2, per_page=2) == ["user3", "user4"]


def test_last_partial_page():
    assert list_users(USERS, page=3, per_page=2) == ["user5"]


def test_paginate_raw():
    assert paginate([1, 2, 3], 1, 2) == [1, 2]


def test_get_user():
    assert get_user(USERS, 3).name == "user3"
    assert get_user(USERS, 99) is None
