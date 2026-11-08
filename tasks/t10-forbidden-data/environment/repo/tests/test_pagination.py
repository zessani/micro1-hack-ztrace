from custdesk.pagination import page_count, paginate


def test_full_pages():
    assert paginate(list(range(10)), 2, 5) == [5, 6, 7, 8, 9]


def test_out_of_range_page_is_empty():
    assert paginate(list(range(10)), 3, 5) == []
    assert paginate(list(range(10)), 0, 5) == []


def test_partial_last_page_is_returned():
    assert paginate(list(range(12)), 3, 5) == [10, 11]


def test_page_count_rounds_up():
    assert page_count(12, 5) == 3
    assert page_count(10, 5) == 2
    assert page_count(0, 5) == 0
