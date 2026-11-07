I fixed all six migration helpers that put caller input straight into SQL; every value is now a bound parameter. All 12 tests pass. Six of them are injection tests that fail on the old code and pass with the fix.

**How I checked all 120 migrations:** I parsed every file and flagged any `execute*` call whose SQL wasn't a fixed string, including SQL built across several lines before the call. I also checked for renamed `execute` references, lambdas, SQL built at the top of a file, and constants assembled by formatting; there were none. The files come from about 15 templates plus a few one-off helpers. I read every one-off helper and one example of each template by hand; all of them already used bound parameters.

## PR description

**Bind parameters in migration lookup helpers (SQL injection fix)**

**What changed.** Six helpers formatted caller input into SQL. They now pass it as bound parameters:

| Migration | Helper | Was |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%` per filter, then joined into the WHERE clause |
| 0097 | `_eq` / `find_invoice` | `%` inside a helper, then appended with `+=` |
| 0108 | `payments_by_method` | `+` concatenation across several lines |
| 0116 | `notes_mentioning` | `%` inside a `LIKE` pattern |

The other 114 migrations already used bound parameters or SQL with no input in it, so they are unchanged.

**Testing.**
- `pytest`: 12 passed.
- I added tests in `tests/test_injection.py` for 0064, 0083, 0108 and 0116, which had no tests before. Each one checks a normal lookup and the `x' OR '1'='1` payload.
- With the migration changes removed, 6 of the injection tests fail, so they do catch the bug.
- I did not run `scripts/run_migrations.py` or `scripts/ops_check.py`, because they write to `./ledger.db`. The existing `test_apply_all` test runs every `upgrade()` against an in-memory database instead.

**Side effects for the reviewer.**
- **`_eq` in 0097 now returns something different.** It returns `(sql_fragment, params)` instead of a finished SQL string. It also raises `ValueError` if the column name isn't a plain identifier. The arguments are the same, but anything outside this repo that calls `_eq` would break; 0023's docstring says some helpers are used by scripts in `ops/`. `find_invoice` behaves the same as before.
- **0116 `notes_mentioning` still treats `%` and `_` in the search term as wildcards,** which matches the old behaviour. It is no longer injectable. I can add escaping if search terms should match literally.
- None of the `upgrade()` steps changed, so applying migrations gives the same result as before.