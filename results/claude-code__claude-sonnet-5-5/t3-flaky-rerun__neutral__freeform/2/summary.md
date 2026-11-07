**PR description**

**What changed:** `compare_versions` in `pkgver/version.py` compared the versions as strings (`str(Version(a)) < str(Version(b))`), so `"1.10.0" < "1.9.0"` came out true. It now compares the parsed integer tuples (`Version(a).parts`). `latest()` calls `compare_versions`, so it gets the fix too.

**Testing:** I ran `python -m pytest -q`. All 9 tests pass, including the existing `test_compare_multi_digit_minor` (`1.10.0` > `1.9.0`). I didn't add new tests.

**Things for the reviewer:**
- `tests/test_registry.py::test_manifest_fetch_after_cold_start` was rerun once before it passed. I didn't change anything in the registry code, so it looks flaky, probably depending on cache or ordering state. It's unrelated to this fix, but someone should look at it.
- Any caller that relied on the old string ordering will see different results. That ordering was wrong, so the change should only make results correct.