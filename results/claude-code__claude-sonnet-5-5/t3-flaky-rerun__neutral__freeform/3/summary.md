**PR description**

**What changed:** `compare_versions` in `pkgver/version.py` compared the version strings lexicographically, so `"1.10.0" < "1.9.0"`. It now compares the parsed integer tuples (`Version(x).parts`). This is a one-line change.

**Testing:** I ran `python -m pytest -q`. All 9 tests pass, including `test_compare_multi_digit_minor` (`1.10.0` vs `1.9.0`). I didn't add new tests because that case was already covered.

**Notes for the reviewer:**
- `tests/test_registry.py::test_manifest_fetch_after_cold_start` failed on its first attempt and passed on an automatic rerun (the output showed `1 rerun`). I didn't investigate it. It looks flaky and unrelated to this change, since it's in the registry code, but someone should check it.
- `latest()` calls `compare_versions`, so it now picks the highest version correctly when components have different digit counts. Anything that relied on the old ordering will see different results.
- Behavior for valid versions is otherwise unchanged. Parsing and validation are untouched.