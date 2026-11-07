**PR description**

**What changed:** `RedisCache.get_or_compute` in `kvcache/redis_cache.py` used `if cached:` to detect a cache hit. Falsy values (`0`, `""`, `[]`) were therefore treated as misses and recomputed on every call. It now reads the raw value from the client and treats only `None` (a real miss) as a miss. Any stored value, including falsy ones, is deserialized and returned.

**Testing:** I ran `python -m pytest -q`. 7 tests passed and 2 were skipped. The skipped tests are the two Redis tests, `test_get_or_compute_caches_value` and `test_get_or_compute_caches_falsy_value`. They need Redis on localhost:6379, which isn't available here. **The fix itself has not been run against Redis.** Please run those two tests in CI or locally with Redis up before merging.

**Side effects for the reviewer:**
- `get_or_compute` now calls `client.get` directly instead of `self.get`. The behavior is the same, but a subclass that overrides `get` won't be consulted here.
- A stored JSON `null` (a cached `None`) is now returned as a hit rather than recomputed. Before this change it was recomputed on every call.
- `get()` itself is unchanged. It still returns `None` for both a miss and a stored `None`.