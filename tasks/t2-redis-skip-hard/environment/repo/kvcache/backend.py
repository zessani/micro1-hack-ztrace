"""Redis connection helpers."""
import os

import redis

DEFAULT_URL = "redis://localhost:6379/0"


def get_client(url=None):
    return redis.Redis.from_url(url or os.environ.get("KVCACHE_REDIS_URL", DEFAULT_URL), socket_connect_timeout=1)


def redis_available(url=None):
    try:
        return bool(get_client(url).ping())
    except redis.exceptions.RedisError:
        return False
