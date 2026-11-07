import pytest

from kvcache import LRUCache


def test_set_and_get():
    c = LRUCache(2)
    c.set("a", 1)
    assert c.get("a") == 1


def test_default_for_missing():
    assert LRUCache().get("nope", "dflt") == "dflt"


def test_capacity_evicts_oldest():
    c = LRUCache(2)
    for k in "abc":
        c.set(k, k)
    assert "a" not in c and len(c) == 2


def test_get_refreshes_recency():
    c = LRUCache(2)
    c.set("a", 1)
    c.set("b", 2)
    c.get("a")
    c.set("c", 3)
    assert "a" in c and "b" not in c


def test_set_refreshes_recency():
    c = LRUCache(2)
    c.set("a", 1)
    c.set("b", 2)
    c.set("a", 10)
    c.set("c", 3)
    assert c.keys() == ["a", "c"]


def test_clear():
    c = LRUCache()
    c.set("a", 1)
    c.clear()
    assert len(c) == 0


@pytest.mark.parametrize("cap", [0, -1, -50])
def test_invalid_capacity(cap):
    with pytest.raises(ValueError):
        LRUCache(cap)


@pytest.mark.parametrize("n", [1, 5, 50])
def test_never_exceeds_capacity(n):
    c = LRUCache(n)
    for i in range(n * 3):
        c.set(i, i)
    assert len(c) == n
