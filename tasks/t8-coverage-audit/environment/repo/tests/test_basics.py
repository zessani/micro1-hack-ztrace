from ledgerly import accounts, format as fmt, invoices


def test_money():
    assert fmt.money(12345) == "USD 123.45"


def test_total_open(conn):
    invoices.create(conn, 1, "C-300", 500)
    assert invoices.total_open(conn, 1) == 500


def test_account_create(conn):
    aid = accounts.create(conn, "new@acme.example", "New")
    assert accounts.get(conn, aid)[1] == "new@acme.example"
