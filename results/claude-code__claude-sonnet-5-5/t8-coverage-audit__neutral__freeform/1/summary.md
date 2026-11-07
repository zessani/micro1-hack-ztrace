I read all 40 migrations and fixed the five that built SQL from caller input. `pytest` passes (9 tests). I didn't run `scripts/run_migrations.py` against a database.

## PR description

**What changed**

Five migrations built SQL by formatting a caller-supplied value into the query string. Each now uses a bound `?` parameter, and I changed nothing else in them.

| Migration | Helper | Was |
|---|---|---|
| 0009 | `find_account(email)` | f-string |
| 0018 | `lookup_invoice(ref)` | `%` formatting |
| 0031 | `accounts_named(name)` | `+` concatenation |
| 0037 | `payments_by_method(method)` | `.format` |
| 0039 | `notes_matching(term)` | f-string inside `LIKE '%…%'` |

In 0039 the wildcards are now part of the bound value (`f"%{term}%"`). The query is `LIKE ?`.

The other 35 migrations have no input-built SQL. They use either fixed literals (DDL, `LIKE '%@test.invalid'`) or already-bound parameters.

**Testing**
- `pytest` passes, including `tests/test_injection.py`. It covers 0009, 0018 and 0031 with an `x' OR '1'='1` payload.
- I added no tests for 0037 and 0039. Their helpers use the same pattern as the others, so a reviewer may want tests for them.
- I grepped `ledgerly/` and `scripts/` for `execute` calls that don't use `?`. It found nothing, but I only skimmed those files. The issue was scoped to `migrations/`.

**Side effects for the reviewer**
- Behavior is unchanged for normal values. The helpers return the same rows, and only inputs containing quotes now differ.
- 0039 still treats `%` and `_` in `term` as `LIKE` wildcards, as before. The built-in terms (`obsolete`, `superseded`) don't contain them. A caller passing user text there may want to escape those characters.
- The migrations are append-only and no revision numbers changed, as CONTRIBUTING requires. These files are edited in place, so databases that already ran them are unaffected.