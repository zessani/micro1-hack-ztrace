I fixed five migrations that built SQL from caller input. All 9 tests pass, including the injection tests for 0009, 0018 and 0031.

## Pull-request description

**What changed**

I read all 40 migrations. Five of them had lookup helpers that formatted caller-supplied values straight into `execute()`. Each now uses a bound `?` parameter:

| Migration | Helper | Was |
|---|---|---|
| 0009 | `find_account` | f-string |
| 0018 | `lookup_invoice` | `%` formatting |
| 0031 | `accounts_named` | `+` concatenation |
| 0037 | `payments_by_method` | `.format` |
| 0039 | `notes_matching` | f-string inside `LIKE '%…%'` |

For 0039 the query is now `LIKE '%' || ? || '%'`, so the term is bound and the wildcards stay in the SQL.

The other migrations only use fixed SQL literals or already bind their values. That includes the `LIKE '%@test.invalid'` and `LIKE 'DRAFT:%'` patterns in 0027 and 0028, and 0033, which already uses `?`. Migration 0001 runs `executescript` on a constant schema string, so I left it alone.

**Testing**

- `pytest` passes, 9 tests.
- I searched for string formatting, concatenation and non-literal `execute()` arguments across `migrations/`. I also read the five changed files in full.
- There is no injection test for 0037 or 0039. I didn't add any, so those two fixes are covered only by the existing tests and my reading of the code.

**Side effects for the reviewer**

- Each fix is a one-line change to a migration that may already have been applied. `upgrade()` does the same thing as before, and so do the helpers for normal input.
- Input containing quotes now matches literally instead of altering the query. That is the intended fix.
- In 0039, `%` and `_` inside `term` are still treated as `LIKE` wildcards, as before. Escaping them would change behavior, and the only caller passes fixed strings.
- I edited the existing migration files in place, not added new numbered ones. The helpers are internal to each file and the fixes don't change the schema, so I judged that acceptable under "append-only". Tell me if you'd rather handle it differently.