## PR description

**What changed**

I audited all 40 migrations. Five built SQL by string formatting, and each one is now a bound parameter. All five are lookup helpers that take caller input:

| Migration | Function | Was | Now |
|---|---|---|---|
| 0009 | `find_account` | f-string | `?` |
| 0018 | `lookup_invoice` | `%` | `?` |
| 0031 | `accounts_named` | `+` concatenation | `?` |
| 0037 | `payments_by_method` | `.format` | `?` |
| 0039 | `notes_matching` | f-string inside `LIKE '%…%'` | `LIKE '%' || ? || '%'` |

The other 35 migrations use only constant SQL or already-bound parameters, so I left them alone. That includes the `LIKE '%…'` literals in 0027 and 0028. The `upgrade()` functions were already parameterized. Nothing outside `migrations/` needed changes. I didn't renumber or add migrations, as CONTRIBUTING requires.

**Testing**

- `pytest` passes (9 tests), including the existing injection tests for 0009, 0018 and 0031.
- `scripts/run_migrations.py` applies all 40 migrations without errors.
- There are no injection tests for 0037 or 0039, so those two fixes are covered only by the migration run, not by a test.

**Side effects for the reviewer**

- Results for normal input are unchanged.
- In 0039, `%` and `_` inside `term` still act as `LIKE` wildcards. That's the same as before, and it isn't an injection risk. If the term should match literally, it needs `ESCAPE` handling, which I didn't add. The current `STALE_MARKERS` are unaffected.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>