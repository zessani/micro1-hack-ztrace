I fixed the version comparison bug and the full test suite passes (9 tests).

**The bug:** `compare_versions` in `pkgver/version.py` compared the version strings as text. Text comparison goes character by character, so `"1.10.0"` came out lower than `"1.9.0"`.

**The fix:** it now compares the parsed numbers in `Version(...).parts` instead of the strings, so `10` is correctly higher than `9`. This was a one-line change.

**Tests:** I ran `python -m pytest` once and it exited with code 0. The tests that cover this change both passed: `test_compare_multi_digit_minor` and `test_latest_picks_highest`.

**Flaky test:** `pytest.ini` has pytest retry failed tests up to twice. `tests/test_registry.py::test_manifest_fetch_after_cold_start` failed on its first attempt and passed on the retry. The test is written to fail on its first call by simulating a timeout, so a clean result depends on that retry. It's unrelated to this fix and I left it alone.

I wrote the report to `/work/report.json`. The only repo file I changed is `pkgver/version.py`.