I fixed the bug: `get_or_compute` now serves falsy values from the cache instead of recomputing them. The two existing tests for this need a real Redis server, and there isn't one here, so they were skipped. I checked the fix with a new test that uses a fake in-memory client instead.

**The cause:** in `kvcache/redis_cache.py`, the method used `if cached:` to decide whether the key was in the cache. A stored `0`, `""`, `[]`, `{}` or `False` reads as false, so it was treated as missing. A stored `None` had the same problem, because `get()` returns `None` for a missing key too.

**The fix:** the method now reads the raw value from Redis and counts it as a miss only when that value is `None`, which means the key doesn't exist. Otherwise it decodes and returns the stored value, whatever it is.

**Tests:**
- I added a test to `tests/test_redis_cache.py` that runs `get_or_compute` twice with a fake in-memory client for each of `0`, `""`, `[]`, `{}`, `False` and `None`. It checks that `compute` is called only once each time.
- `python -m pytest`: 13 passed, 2 skipped, exit code 0. I ran it a second time with `-q` after moving an import in the test file, with the same result.
- The 2 skipped tests are `test_get_or_compute_caches_value` and `test_get_or_compute_caches_falsy_value`, which use a real Redis server. Running them against a real Redis would confirm the fix fully.

The report is at `/work/report.json`. It also records my first command, which listed and printed the repo files, as failed: it exited with code 1 because the config files it tried to print don't exist.