I fixed all six injectable helpers. `pytest` passes (8 tests). I did not run `scripts/run_migrations.py` or `scripts/ops_check.py`.

## PR description

**What changed**

I checked all 120 migrations with an AST scan. It flags every `execute`, `executemany` and `executescript` call whose SQL isn't a literal or a module-level string constant, and it also lists every helper function. Reading the flagged calls turned up six injectable helpers. Each now uses bound parameters:

| Migration | Helper | Problem |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%` formatting, built up clause by clause |
| 0097 | `find_invoice` | built in steps through a `_eq()` helper, which I removed |
| 0108 | `payments_by_method` | `+` concatenation |
| 0116 | `notes_mentioning` | `%` formatting inside a `LIKE` pattern |

- In 0083 the WHERE clauses are now `?` placeholders with a separate params list. The SQL text only ever contains fixed fragments.
- 0116 binds the `LIKE` pattern as `"%" + term + "%"`.
- Nothing else in `migrations/` builds SQL from input. The remaining `%` formatting is for log and summary strings, and `executescript` is only called on constant DDL.

**Testing**
- `pytest`: 8 passed, including `tests/test_injection.py`, which covers 0023 and 0097.
- I ran the AST scan again after the fixes. It now flags only 0083, which passes a params list alongside fixed SQL text.
- I checked 0116 by hand with an injection payload (no match), and with `%` and `_` searches (they match literally).

**Side effects for the reviewer**
- **0116 behaviour change:** the old code treated `%` and `_` in a search term as wildcards. I escape them (`ESCAPE '\'`), so they now match literally. Drop `_like_escape` if you want wildcards back. It is still injection-safe either way.
- **No new tests:** I only checked the four helpers without tests (0064, 0083, 0108, 0116) manually, and added none, so a follow-up could add injection tests for them.
- **Scope:** no schema or data changes, and the migrations aren't renumbered, so the append-only rule is untouched. I edited the helper code in place, and `upgrade()` is unchanged.

I haven't committed anything.