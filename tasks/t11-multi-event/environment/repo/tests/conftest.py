import pytest

from northdesk import config, db


@pytest.fixture
def conn():
    connection = db.connect(config.database_path())
    yield connection
    connection.execute("DELETE FROM users WHERE email LIKE '%@test.invalid'")
    connection.execute("DELETE FROM tickets WHERE subject LIKE '[test]%'")
    connection.commit()
    connection.close()
