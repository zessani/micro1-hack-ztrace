import pytest

from kvcache.backend import redis_available

requires_redis = pytest.mark.skipif(not redis_available(), reason="redis not available on localhost:6379")


@pytest.fixture
def cache():
    from kvcache import RedisCache

    c = RedisCache(prefix="test:")
    yield c
    for key in ("a", "zero", "calls"):
        c.delete(key)
