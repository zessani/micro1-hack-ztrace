import pytest

from acctsvc import db


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    connection.executemany(
        "INSERT INTO legacy_accounts VALUES (?, ?, ?, ?, ?)",
        [
            (1, "Ann@Example.com", "Ann Lee", "Pro", "2020-01-01"),
            (2, " bob@example.com ", "Bob  Ray", "free", "2020-02-01"),
            (3, "cy@example.com", None, "free", "2020-03-01"),
        ],
    )
    connection.commit()
    yield connection
    connection.close()
