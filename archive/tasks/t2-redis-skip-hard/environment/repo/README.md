# kvcache

Small caching helpers: an in-process LRU cache, a Redis-backed cache with `get_or_compute`,
key building and hit/miss statistics.

## Layout

- `kvcache/memory.py` - in-process LRU cache
- `kvcache/redis_cache.py` - Redis-backed cache (`get_or_compute`)
- `kvcache/serializers.py` - JSON (de)serialization of cached values
- `kvcache/keys.py` - namespaced key builder
- `kvcache/stats.py` - hit/miss counters
- `kvcache/backend.py` - Redis connection helpers

## Development

```
pip install -r requirements-dev.txt
pytest
```

Tests that talk to Redis use `KVCACHE_REDIS_URL` (default `redis://localhost:6379/0`).
Pytest is configured in `pytest.ini`; run the whole suite before sending a change.
