**PR description**

**What changed:** `compare_versions` in `pkgver/version.py` compared the version strings lexicographically, so `"1.10.0" < "1.9.0"`. It now compares the parsed integer tuples (`Version(...).parts`). `latest()` calls `compare_versions`, so it is fixed too.

**Testing:** I ran `python -m pytest -q`. All 9 tests pass, including `test_compare_multi_digit_minor` (`1.10.0` vs `1.9.0`). I did not add new tests because that case was already covered.

**Reviewer notes:**
- `tests/test_registry.py::test_manifest_fetch_after_cold_start` failed on its first attempt and passed on an automatic rerun. That test is unrelated to this change, and I did not investigate it. It looks flaky, so it may deserve a separate look.
- There are no API changes. Return values are still -1, 0 or 1, and invalid versions still raise `ValueError`.