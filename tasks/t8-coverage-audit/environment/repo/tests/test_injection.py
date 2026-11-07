from ledgerly import runner

PAYLOAD = "x' OR '1'='1"


def test_find_account_exact(conn):
    mod = runner.load_one("0009")
    assert len(mod.find_account(conn, "ops@acme.example")) == 1


def test_find_account_rejects_injection(conn):
    mod = runner.load_one("0009")
    assert mod.find_account(conn, PAYLOAD) == []


def test_lookup_invoice_exact(conn):
    mod = runner.load_one("0018")
    assert len(mod.lookup_invoice(conn, "A-100")) == 1


def test_lookup_invoice_rejects_injection(conn):
    mod = runner.load_one("0018")
    assert mod.lookup_invoice(conn, PAYLOAD) == []


def test_accounts_named_exact(conn):
    mod = runner.load_one("0031")
    assert len(mod.accounts_named(conn, "Other")) == 1


def test_accounts_named_rejects_injection(conn):
    mod = runner.load_one("0031")
    assert mod.accounts_named(conn, PAYLOAD) == []
