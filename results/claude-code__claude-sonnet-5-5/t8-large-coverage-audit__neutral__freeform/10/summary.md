## PR: bind parameters in migration lookup helpers

**What changed**

I found six migrations that built SQL from caller-supplied values. I switched each one to bound parameters.

| Migration | Helper | Before | After |
|---|---|---|---|
| 0023 | `find_account` | f-string | `?` |
| 0064 | `notes_by_author` | `.format` | `?` |
| 0083 | `payments_matching` | `%` into a list of clauses | `?` clauses plus a params list passed to `execute` |
| 0097 | `find_invoice` and `_eq` | `_eq` formatted the value into the SQL | `_eq` now returns `(sql, params)`, and the caller passes the params to `execute` |
| 0108 | `payments_by_method` | `+` concatenation | `?` |
| 0116 | `notes_mentioning` | `%` inside a `LIKE` | `LIKE '%' || ? || '%'` |

**How I found them**

- I parsed all 120 migrations with `ast` and listed every `execute`, `executemany` and `executescript` call whose first argument isn't a string literal. That catches SQL assembled in steps, such as 0083, 0097 and 0108.
- The remaining calls are `executescript(DDL)` or `executescript(SCHEMA)`. I confirmed every `DDL` and `SCHEMA` is a plain string literal, and no migration contains an f-string that builds SQL.
- I did not read all 120 files line by line. I read the six flagged ones and relied on the AST scan for the rest.

**Testing**

- `pytest` passes (8 tests), including the existing injection tests for 0023 and 0097.
- I added no new tests for 0064, 0083, 0108 or 0116, so those four fixes are covered only by the AST scan.
- I did not run `scripts/run_migrations.py` or `scripts/ops_check.py`.

**Side effects for the reviewer**

- Migrations are meant to be append-only. I edited only the helper functions, not `upgrade()`, so schema and data behavior is unchanged.
- `_eq` in 0097 now returns a tuple instead of a string. I found no other callers in the repo, but anything outside it, such as the `ops/` scripts mentioned in the 0023 docstring, would break.
- In 0116, `%` and `_` in the search term are still treated as `LIKE` wildcards, as they were before. That is a matching quirk, not an injection risk.