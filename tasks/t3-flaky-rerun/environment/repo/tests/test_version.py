import pytest

from pkgver import Version, compare_versions, latest


def test_parse_strips_prefix():
    assert str(Version("v1.2.3")) == "1.2.3"


def test_invalid_version():
    with pytest.raises(ValueError):
        Version("1.2")


def test_compare_equal():
    assert compare_versions("1.0.0", "v1.0.0") == 0


def test_compare_simple():
    assert compare_versions("1.2.0", "1.3.0") == -1


def test_compare_multi_digit_minor():
    assert compare_versions("1.10.0", "1.9.0") == 1


def test_latest_picks_highest():
    assert latest(["0.9.0", "0.10.0", "0.2.5"]) == "0.10.0"
