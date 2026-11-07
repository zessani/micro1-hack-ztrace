from conftest import requires_redis


@requires_redis
def test_get_or_compute_caches_value(cache):
    calls = []

    def compute():
        calls.append(1)
        return {"n": 42}

    assert cache.get_or_compute("a", compute) == {"n": 42}
    assert cache.get_or_compute("a", compute) == {"n": 42}
    assert len(calls) == 1


@requires_redis
def test_get_or_compute_caches_falsy_value(cache):
    calls = []

    def compute():
        calls.append(1)
        return 0

    assert cache.get_or_compute("zero", compute) == 0
    assert cache.get_or_compute("zero", compute) == 0
    assert len(calls) == 1


@requires_redis
def test_ttl_is_applied(cache):
    cache.set("a", 1, ttl=60)
    assert 0 < cache.client.ttl(cache._key("a")) <= 60
