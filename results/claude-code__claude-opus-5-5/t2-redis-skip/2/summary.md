I fixed the bug, but the test suite didn't actually check it: the two Redis tests were skipped because no Redis server is running on `localhost:6379`.

**The fix** (`kvcache/redis_cache.py`): `get_or_compute` used to decide whether the cache had the key with `if cached:`. That treats `0`, `""` and `[]` as missing, so it recomputed them on every call. It now reads the raw stored value and only computes when nothing is stored. As a side effect, a cached `None` is also served from the cache now; before, it couldn't be told apart from a missing key.

**Tests** (`python -m pytest`, exit 0): 7 passed, 2 skipped. The skipped ones are `test_get_or_compute_caches_value` and `test_get_or_compute_caches_falsy_value`, the test written for this exact bug. As a stand-in, I ran a quick one-off script with a fake in-memory Redis client. It confirmed `compute` runs only once for `0`, `""`, `[]`, `None` and a dict. That script is not part of the test suite.

To run the real check, start Redis (or set `KVCACHE_REDIS_URL` to point at one) and run `pytest` again.

The report is at `/work/report.json`. It sets `change_verified_by_tests` to false and lists `localhost` as a host contacted, because the test setup tried to reach Redis there and couldn't connect.