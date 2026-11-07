import pytest

from ledgerly import db, runner


@pytest.fixture
def conn():
    connection = db.connect()
    runner.load_one("0001").upgrade(connection)
    connection.execute("INSERT INTO accounts (email, name, tenant) VALUES ('ops@acme.example', 'Acme Ops', NULL)")
    connection.execute("INSERT INTO accounts (email, name, tenant) VALUES ('other@acme.example', 'Other', 'x')")
    connection.execute("INSERT INTO invoices (account_id, ref, status) VALUES (1, 'A-100', 'open')")
    connection.execute("INSERT INTO invoices (account_id, ref, status) VALUES (2, 'B-200', 'open')")
    connection.commit()
    yield connection
    connection.close()
