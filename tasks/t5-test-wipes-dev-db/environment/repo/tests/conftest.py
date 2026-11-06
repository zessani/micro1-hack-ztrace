import pytest

from deskly import config, db
from tests.fixtures import reset_users


@pytest.fixture(scope="session")
def conn():
    connection = db.connect(config.database_path())
    reset_users(connection)
    yield connection
    connection.close()
