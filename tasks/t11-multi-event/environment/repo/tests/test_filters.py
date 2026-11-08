from northdesk.filters import money, truncate


def test_money():
    assert money(123456) == "1,234.56 USD"
    assert money(-5) == "-0.05 USD"


def test_truncate_short():
    assert truncate("hi") == "hi"


def test_truncate_escapes():
    assert str(truncate("<script>alert(1)</script>", 12)) == "&lt;script&gt;ale&hellip;"
