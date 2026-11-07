## PR: Use bound parameters in migration lookup helpers

**What changed**

I reviewed all 40 migrations. Five built SQL from caller-supplied values with string formatting, so I switched each to a `?` bound parameter. Each change is one line.

| Migration | Helper | Was |
|---|---|---|
| 0009 | `find_account` | f-string |
| 0018 | `lookup_invoice` | `%` formatting |
| 0031 | `accounts_named` | `+` concatenation |
| 0037 | method lookup | `.format` |
| 0039 | `notes_matching` | f-string inside `LIKE '%…%'` |

The other 35 migrations execute only fixed SQL literals with no interpolation. Their remaining `execute()` calls already use `?`. I did not touch those.

**Testing**

- `pytest` passes (9 tests). That includes `tests/test_injection.py`, which covers 0009, 0018 and 0031 with an `x' OR '1'='1` payload.
- `python3 scripts/run_migrations.py` applies all 40 migrations cleanly.
- 0037 and 0039 have no injection tests, so I did not exercise them directly. I'd suggest adding tests for them as a follow-up.

**Notes for the reviewer**

- Behaviour is unchanged for normal inputs. The `upgrade()` paths pass the same values as before.
- 0039 now uses `'%' || ? || '%'`, which keeps the substring-match semantics. As before, a `%` or `_` inside the term acts as a LIKE wildcard. The old code behaved the same way, and the current callers only pass the fixed markers `obsolete` and `superseded`. If the helper is ever exposed to arbitrary input, it would need `ESCAPE` handling.
- I edited already-numbered migrations in place. This keeps their numbering and revision IDs, and the change affects only the helper functions, not the schema or data transformations. Databases that have already applied them are unaffected.