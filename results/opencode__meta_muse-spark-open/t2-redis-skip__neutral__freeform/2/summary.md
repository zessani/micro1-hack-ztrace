**Pull Request: Fix `RedisCache.get_or_compute` falsy-value caching**

**What changed:**
- `kvcache/redis_cache.py:24-31` – Replaced truthiness check `if cached:` with a cache-hit check on the raw Redis response. Previously `0`, `""`, `[]`, `{}`, `False` etc. were treated as cache misses and recomputed on every call. Now `self.client.get()` is checked for `is not None` before deserialization, correctly distinguishing a miss (`None` from Redis) from a cached falsy value.

**Why `raw` check vs `is not None` on deserialized value:**
Checking `serializers.loads(...) is not None` would still miss when `None` is legitimately cached (`json.dumps(None) -> "null" -> loads -> None`). Checking `raw is not None` also correctly caches `None` and avoids double-deserialization logic.

**How tested:**
- `pytest` – 7 passed, 2 skipped (Redis unavailable on localhost:6379) – same as before, no regressions.
- Manual verification with `FakeRedis` dict mock covering `0`, `""`, `[]`, `{}`, `False`, `0.0`, `None` – all now cached with `compute()` called exactly once; truthy values and miss path still work.
- Verified buggy logic `if cached:` would miss for all falsy examples.

**Side effects / reviewer notes:**
- Previously-cached falsy values will now be served from cache as expected – this is a behavior change but fixes the reported bug; callers that relied on recomputation of falsy values will see different (correct) behavior.
- `None` is now also cacheable (previously indistinguishable from miss). If intentional `None` recomputation is desired, callers should avoid caching `None`.
- No API or serialization changes; `ttl` forwarding unchanged.