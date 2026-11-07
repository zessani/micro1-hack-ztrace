import logging

import pytest

from kvcache.backend import redis_available

requires_redis = pytest.mark.skipif(not redis_available(), reason="redis not available on localhost:6379")


@pytest.fixture(autouse=True)
def _log_level(caplog):
    caplog.set_level(logging.INFO)


@pytest.fixture
def cache():
    from kvcache import RedisCache

    c = RedisCache(prefix="test:")
    yield c
    for key in ("a", "zero", "calls"):
        c.delete(key)
