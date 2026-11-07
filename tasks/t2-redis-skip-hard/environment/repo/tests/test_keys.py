import pytest

from kvcache.keys import make_key, split_key


@pytest.mark.parametrize(
    "parts,expected",
    [(("user", 1), "user:1"), (("a",), "a"), (("a", "b", "c"), "a:b:c"), (("x y", "z"), "x_y:z"), (("a", None, "b"), "a:b")],
)
def test_make_key(parts, expected):
    assert make_key(*parts) == expected


def test_empty_key_rejected():
    with pytest.raises(ValueError):
        make_key(None, "")


def test_custom_separator_warns():
    with pytest.warns(DeprecationWarning):
        assert make_key("a", "b", sep="/") == "a/b"


def test_split_roundtrip():
    assert split_key(make_key("a", "b")) == ["a", "b"]
