import pytest

from kvcache import CacheStats


def test_starts_empty():
    s = CacheStats()
    assert s.total == 0 and s.hit_rate == 0.0


@pytest.mark.parametrize("hits,misses,rate", [(1, 1, 0.5), (3, 1, 0.75), (0, 4, 0.0), (4, 0, 1.0)])
def test_hit_rate(hits, misses, rate):
    s = CacheStats()
    for _ in range(hits):
        s.record(True)
    for _ in range(misses):
        s.record(False)
    assert s.hit_rate == rate


def test_reset():
    s = CacheStats()
    s.record(True)
    s.reset()
    assert s.total == 0
