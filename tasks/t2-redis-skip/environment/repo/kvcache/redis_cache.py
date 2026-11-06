"""Redis-backed cache with compute-on-miss."""
from . import serializers
from .backend import get_client


class RedisCache:
    def __init__(self, client=None, prefix="kv:", ttl=300):
        self.client = client or get_client()
        self.prefix = prefix
        self.ttl = ttl

    def _key(self, key):
        return self.prefix + key

    def get(self, key):
        return serializers.loads(self.client.get(self._key(key)))

    def set(self, key, value, ttl=None):
        self.client.set(self._key(key), serializers.dumps(value), ex=ttl or self.ttl)

    def delete(self, key):
        self.client.delete(self._key(key))

    def get_or_compute(self, key, compute, ttl=None):
        """Return the cached value for key, computing and storing it on a miss."""
        cached = self.get(key)
        if cached:
            return cached
        value = compute()
        self.set(key, value, ttl)
        return value
