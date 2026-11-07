I found six migrations that built SQL from caller input and fixed all of them with bound parameters. All 12 tests now pass. I haven't committed anything.

## PR description

**Use bound parameters in migration lookup helpers (SQL injection fix)**

### What changed
All 120 migrations were checked. Six helpers formatted caller-supplied values into SQL; each now binds them:

| Migration | Helper | Was |
|---|---|---|
| `0023` | `find_account` | f-string |
| `0064` | `notes_by_author` | `.format()` |
| `0083` | `payments_matching` | `%`-formatted `WHERE` clauses, joined in steps |
| `0097` | `find_invoice` (through `_eq`) | `_eq()` returned `" AND col = 'value'"` |
| `0108` | `payments_by_method` | `+` concatenation over several lines |
| `0116` | `notes_mentioning` | `%` inside a `LIKE '%…%'` pattern |

- `0083` now collects a `params` list alongside the clauses.
- `0097`'s `_eq()` now returns `(fragment, params)`. Its column name must still be a trusted identifier; `find_invoice` is its only caller.
- `0116` now uses `LIKE '%' || ? || '%'`.
- No `upgrade()` logic or other migration code changed. Following CONTRIBUTING, nothing was renumbered.

### How it was found
I wrote a script that parses each migration and checks every `execute`, `executemany` and `executescript` call. It flags any SQL argument that isn't a constant string, following variables and `+=` steps inside each function. That flagged exactly these six. After the fix, the script still flags `0083` and `0097`, because `sql` is assembled in steps there. I read both: every piece is now a constant and every value is bound. I also confirmed no migration calls `execute` at module level or through an alias.

### Testing
- `pytest`: 12 passed.
- Added tests in `tests/test_injection.py` for `0064`, `0083`, `0108` and `0116` (`0023` and `0097` were already covered). Each checks a normal match and that an injection payload matches nothing.
- With the old migration code, all six injection tests fail; with this change, all pass.
- I did not run `scripts/run_migrations.py` or `scripts/ops_check.py`. They write to `./ledger.db`, and the tests already apply every migration to an in-memory database.

### Side effects for the reviewer
- **`0097._eq()` changed its return type.** It used to return a string and now returns a `(sql, params)` tuple. Nothing in this repo calls it besides `find_invoice`, but code outside the repo that imports it (0023's docstring mentions one-off scripts in `ops/`) would break.
- **Results for legitimate inputs are unchanged.** Values that contain a quote (e.g. `O'Brien`) now match correctly instead of raising a SQL error.
- **In `0116.notes_mentioning`, `%` and `_` typed into the search term still act as wildcards,** as before. The search can't run injected SQL, but it isn't a literal substring match either.