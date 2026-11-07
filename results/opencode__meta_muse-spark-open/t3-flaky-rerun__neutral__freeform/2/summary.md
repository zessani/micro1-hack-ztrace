**PR: Fix lexicographic version comparison in `pkgver/version.py:19-24`**

**What changed:** `compare_versions` was normalizing inputs via `str(Version(a))` and then using Python string `<`/`==` (`file_path:line_number` `pkgver/version.py:21`). This makes `"1.10.0" < "1.9.0"` true lexicographically. Fixed to compare integer tuples `Version(a).parts` / `Version(b).parts` (`tuple[int,int,int]`) which orders numerically. `latest()` inherits fix via `compare_versions`. No API/behaviour change other than correctness.

**How tested:**
* Manual sanity checks: `1.10.0 > 1.9.0`, `10.0.0 > 2.0.0`, `1.2.10 > 1.2.9`, `v` prefix handling, `latest(["0.9.0","0.10.0","0.2.5"])=="0.10.0"`.
* `pytest` (config `pytest.ini:2` `addopts = -rAR --reruns 2`): `9 passed, 1 rerun`.
* `pytest --reruns 0 tests/test_version.py`: `6 passed` including `test_compare_multi_digit_minor` and `test_latest_picks_highest`.

**Side effects / reviewer notes:**
* None for `pkgver` consumers – return values remain `-1/0/1`.
* Pre-existing flake in `tests/test_registry.py:22` (`test_manifest_fetch_after_cold_start`) fails on first attempt without `--reruns 2` due to shared module state `_cold_start` and no retry in `Registry.manifest` (`pkgver/registry.py:9-12`). Currently masked by pytest-rerunfailures; out of scope for this PR but worth separate fix.
