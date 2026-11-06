import pytest

from kvcache import LRUCache


def test_get_missing_returns_default():
    assert LRUCache().get("x", 5) == 5


def test_eviction_order():
    c = LRUCache(2)
    c.set("a", 1)
    c.set("b", 2)
    c.get("a")
    c.set("c", 3)
    assert "b" not in c and "a" in c and "c" in c


def test_len_tracks_capacity():
    c = LRUCache(3)
    for i in range(10):
        c.set(i, i)
    assert len(c) == 3


def test_invalid_capacity():
    with pytest.raises(ValueError):
        LRUCache(0)
