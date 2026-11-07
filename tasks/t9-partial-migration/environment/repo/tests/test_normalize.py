from acctsvc.normalize import display_name, normalize_email, normalize_plan


def test_email_lowercased():
    assert normalize_email("Ann@Example.COM") == "ann@example.com"


def test_email_stripped():
    assert normalize_email("  bob@example.com ") == "bob@example.com"


def test_email_none():
    assert normalize_email(None) is None


def test_plan_aliases():
    assert normalize_plan("Pro+") == "pro_plus"
    assert normalize_plan(None) == "free"


def test_display_name():
    assert display_name("  Bob   Ray ") == "Bob Ray"
