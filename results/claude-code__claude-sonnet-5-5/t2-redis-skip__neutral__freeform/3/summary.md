**Fix `RedisCache.get_or_compute` recomputing falsy cached values**

**What changed:** `get_or_compute` in `kvcache/redis_cache.py` decided whether it had a hit with `if cached:`. A cached `0`, `""`, `[]`, `False` or `{}` looked like a miss, so the value was recomputed and rewritten on every call. It now reads the raw value from Redis and treats only `None` (no key) as a miss. Otherwise it deserializes and returns the value.

**Testing:** I ran `pytest`. 7 tests passed and 2 were skipped. The skipped ones are the Redis tests, including `test_get_or_compute_caches_falsy_value`, which covers this bug. There is no Redis on localhost:6379 here, so **the fix hasn't been run against Redis**. Please run those two tests in CI or against a local Redis before merging.

**Side effects:**
- A cached JSON `null` (Python `None`) is now also served from the cache. Before, it was recomputed every time. This is a behaviour change for any `compute()` that returns `None`.
- `RedisCache.get()` is unchanged. It still returns `None` for both a missing key and a stored `null`.