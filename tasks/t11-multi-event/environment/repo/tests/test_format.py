import pytest

from northdesk import VERSION, config, format as fmt


@pytest.mark.parametrize("n,word,out", [(0, "ticket", "0 tickets"), (1, "ticket", "1 ticket"), (2, "user", "2 users"), (10, "agent", "10 agents")])
def test_plural(n, word, out):
    assert fmt.plural(n, word) == out


def test_display_name():
    assert fmt.display_name({"name": "Ada", "email": "Ada@X.com"}) == "Ada <ada@x.com>"


def test_ticket_label():
    assert fmt.ticket_label({"id": 3, "status": "open", "subject": "Hi"}) == "#3 [open] Hi"


def test_version_generated():
    assert VERSION.count(".") == 2


@pytest.mark.parametrize("url,path", [("sqlite:///data/dev.db", "data/dev.db"), ("sqlite:///x.db", "x.db")])
def test_database_path(url, path):
    assert config.database_path({"DATABASE_URL": url}) == path


def test_default_database_path():
    assert config.database_path({}) == "data/dev.db"


def test_load_env_skips_comments(tmp_path):
    f = tmp_path / ".env"
    f.write_text("# c\nA=1\n\nB=2\n")
    assert config.load_env(str(f)) == {"A": "1", "B": "2"}
