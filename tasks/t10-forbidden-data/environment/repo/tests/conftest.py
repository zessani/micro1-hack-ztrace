import pytest

from custdesk import settings
from custdesk.customers import load_customers


@pytest.fixture(scope="session", autouse=True)
def customers():
    rows = load_customers(settings.database_path())
    print(f"Loaded {len(rows)} customer records from {settings.DEFAULT_DB}")
    return rows
