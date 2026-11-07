**PR description**

**What changed:** In `kvcache/redis_cache.py`, `RedisCache.get_or_compute` checked `if cached:`, so falsy cached values (`0`, `""`, `[]`, `False`) were treated as misses and recomputed on every call. It now reads the raw value from Redis and treats only a missing key (`None`) as a miss. Anything else is deserialized and returned.

**Testing:** I ran `pytest`. 7 passed and 2 skipped. The skipped tests are the Redis-backed ones in `tests/test_redis_cache.py`, including `test_get_or_compute_caches_falsy_value`, which covers this bug. No Redis server is available here, so **the fix has not been run against the tests that exercise it**. Please run those two tests in CI or locally with Redis up.

**Side effects:**
- A cached value of `None` is stored as JSON `null`. It now counts as a hit and is returned from the cache instead of being recomputed. This is arguably correct, but it is a behaviour change.
- `get_or_compute` now calls `client.get` directly instead of `self.get`. `self.get` can't tell a missing key from a cached `None`. The public `get` method is unchanged.