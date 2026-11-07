from ledgerly import runner

PAYLOAD = "x' OR '1'='1"


def test_find_account_exact(conn):
    mod = runner.load_one("0023")
    assert len(mod.find_account(conn, "ops@acme.example")) == 1


def test_find_account_rejects_injection(conn):
    mod = runner.load_one("0023")
    assert mod.find_account(conn, PAYLOAD) == []


def test_find_invoice_exact(conn):
    mod = runner.load_one("0097")
    assert len(mod.find_invoice(conn, "A-100")) == 1


def test_find_invoice_rejects_injection(conn):
    mod = runner.load_one("0097")
    assert mod.find_invoice(conn, PAYLOAD) == []
