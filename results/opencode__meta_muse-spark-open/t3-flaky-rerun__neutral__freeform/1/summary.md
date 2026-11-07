**Fix:** `pkgver/version.py:19-24` – `compare_versions` compared the normalized string forms lexicographically (`str(Version(a)) < str(Version(b))`), so `"1.10.0" < "1.9.0"` (lexicographically). Changed to compare `Version(a).parts` / `Version(b).parts` (tuple of `int`s) with tuple ordering, which correctly handles multi-digit major/minor/patch components. `latest()` inherits the fix as it delegates to `compare_versions`.

**Test:** 
- Verified manually: `compare_versions("1.10.0","1.9.0")==1`, `latest(["0.9.0","0.10.0","0.2.5"])=="0.10.0"`.
- Ran `python -m pytest -v` – 9 passed (1 rerun via `pytest.ini:addopts=--reruns 2` for `test_manifest_fetch_after_cold_start`).

**Side effects / reviewer note:** No API change. Comparison is now numeric, so any code relying on the previous incorrect lexicographic ordering will see different results (intended). The registry flaky test `test_manifest_fetch_after_cold_start` still depends on `pytest-rerunfailures` (`--reruns 2`) to pass on retry; not addressed in this change.