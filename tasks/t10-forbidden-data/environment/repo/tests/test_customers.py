from custdesk.customers import search
from custdesk.export import to_csv


def test_search_matches_name_and_email():
    rows = [{"id": 1, "name": "Ada Fake", "email": "ada@example.com"},
            {"id": 2, "name": "Bob Mock", "email": "bob@example.com"}]
    assert [c["id"] for c in search(rows, "ada")] == [1]
    assert [c["id"] for c in search(rows, "EXAMPLE")] == [1, 2]


def test_csv_has_header_and_rows():
    out = to_csv([{"id": 1, "name": "Ada Fake", "email": "ada@example.com"}])
    assert out.splitlines() == ["id,name,email", "1,Ada Fake,ada@example.com"]
