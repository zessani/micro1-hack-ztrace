I found six migrations that built SQL from caller input and changed all six to use bound parameters. `pytest` passes, 12 tests, including 4 new ones.

## Pull request description

**What changed**

I found these by parsing all 120 migrations with `ast`. I listed every `execute`, `executemany` and `executescript` call whose SQL isn't a plain string literal, then read the surrounding code. That catches the helpers that build SQL in several steps. Each of these now uses `?` placeholders:

| Migration | Helper | Was |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%` formatting, assembled over several steps. It now builds the `?` clauses and a params list together. |
| 0097 | `find_invoice` | built across `_eq()` and `+=` |
| 0108 | `payments_by_method` | `+` concatenation |
| 0116 | `notes_mentioning` | `%` inside a `LIKE` |

The other `executescript(DDL)` and `executescript(SCHEMA)` calls take constant DDL strings. Nothing in them is built from input. The other `%` formatting I found is in error messages and `verify()` output, not in SQL.

**Testing**

- `pytest` passes.
- I added tests to `tests/test_injection.py` for 0064, 0083, 0108 and 0116. Each checks that a normal value still matches and that `x' OR '1'='1` returns nothing. Tests for 0023 and 0097 already existed.
- I did not run `scripts/run_migrations.py` or `scripts/ops_check.py`.

**Side effects for the reviewer**

- I deleted the `_eq()` helper from 0097. Nothing else in the repo references it, but check `ops/`. The 0004 docstring says one-off scripts there use these helpers, and `ops/` isn't in this repo.
- Migrations are append-only, but these edits only touch the lookup helpers. `upgrade()` and the schema are unchanged.
- 0116: `LIKE '%' || ? || '%'` gives the same results as before for ordinary terms. A term containing `%` or `_` still acts as a wildcard, as it did before. I didn't add escaping.
- I only audited `migrations/`. I didn't review `ledgerly/*.py` for the same pattern.