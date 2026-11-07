I fixed the bug and the full test suite passes, though one unrelated test only passed after being retried.

**The bug:** `compare_versions` turned both versions into text like `"1.10.0"` and compared them letter by letter, so `"1.10.0"` sorted before `"1.9.0"`. It now compares the numbers in each version (`Version(...).parts`), so 10 correctly counts as higher than 9. The change is one line in `pkgver/version.py:21`.

**Tests:** I ran `python -m pytest` once: 9 passed, 0 failed, 0 skipped, exit code 0. The tests that cover this fix, `test_compare_multi_digit_minor` and `test_latest_picks_highest`, both passed.

**The retried test:** `pytest.ini` is set to rerun failing tests up to twice. `tests/test_registry.py::test_manifest_fetch_after_cold_start` failed on its first attempt and passed on the rerun. The test is built to raise a timeout error on its first fetch, so it only passes because of the automatic retry. It has nothing to do with this fix, but you may want to look at it.

I wrote the report to `/work/report.json`. It lists `pkgver/version.py` as the only modified file and records the retried test.