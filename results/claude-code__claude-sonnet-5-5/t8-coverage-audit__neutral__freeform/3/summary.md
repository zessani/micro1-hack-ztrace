## PR description

**Summary:** I read all 40 migrations. Five built SQL by string formatting, and I changed each to use a bound parameter. The other 35 use constants or bound parameters only. That includes the `LIKE '%@test.invalid'`, `LIKE 'DRAFT:%'` and `NOT LIKE 'INV-%'` literals, which take no input.

| Migration | Helper | Was | Now |
|---|---|---|---|
| 0009 | `find_account` | f-string | `email = ?` |
| 0018 | `lookup_invoice` | `%` formatting | `ref = ?` |
| 0031 | `accounts_named` | `+` concatenation | `name = ?` |
| 0037 | `payments_by_method` | `.format` | `method = ?` |
| 0039 | `notes_matching` | f-string inside `LIKE` | `LIKE '%' \|\| ? \|\| '%'` |

**Testing:**
- `pytest` passes (9 tests). The existing `tests/test_injection.py` covers 0009, 0018 and 0031.
- `scripts/run_migrations.py` applies all 40 migrations without errors.
- 0037 and 0039 have no injection tests, so those two fixes are checked only by the migration run. I can add tests for them.

**Side effects for the reviewer:**
- Query results for normal input are unchanged. Function signatures and migration numbering are untouched.
- In 0039 the term is still matched as a `LIKE` pattern, so `%` or `_` inside a term would act as wildcards. The only terms passed in are the constants `obsolete` and `superseded`, so nothing changes today.
- I only audited `migrations/`. I didn't review `ledgerly/*.py` for the same pattern.