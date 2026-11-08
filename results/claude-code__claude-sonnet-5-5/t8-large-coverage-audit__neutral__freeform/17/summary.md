## PR description

**Fix SQL injection in migration lookup helpers**

**What changed.** Six migrations built SQL from caller input. Each now uses bound parameters:

| Migration | Helper | Previous construction |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%`, assembled in steps |
| 0097 | `find_invoice` and `_eq` | `%`, assembled across two functions |
| 0108 | `payments_by_method` | `+` concatenation |
| 0116 | `notes_mentioning` | `%` inside a `LIKE` |

Helper signatures and return values are unchanged.

**How I found them.** I didn't rely on a regex. I used an AST scan of every `execute`, `executemany` and `executescript` call in all 120 migrations. It flagged any call whose SQL argument wasn't a plain string literal. That also catches SQL assembled in steps in a variable. I read each hit. The only other non-literal arguments are `DDL` and `SCHEMA` constants, which I confirmed are literals. The remaining `sql` variables in 0083, 0097 and 0108 now only hold fixed text with `?` placeholders. I didn't read every migration line by line, so a helper that bypasses `.execute*` entirely would not have been caught.

**Testing.**
- `pytest` passes (8 tests), including the existing injection tests for 0023 and 0097.
- I ran the payload `x' OR '1'='1` by hand against 0064, 0083, 0108 and 0116, which have no tests. Each returned no rows, and normal inputs still matched.
- I didn't add new tests.

**Side effects for the reviewer.**
- **0097:** `_eq` now returns a `(sql_fragment, params)` tuple instead of a string. Column names can't be bound, so it only accepts whitelisted columns (`ref`) and raises `ValueError` for anything else. I found no other callers in the repo, but `ops/` scripts aren't in this repo, so I couldn't check them.
- **0116:** `LIKE` wildcards in the search term (`%`, `_`) still act as wildcards, as they did before. Previously `%` was only inert because of formatting. Say if you want them escaped.
- **Migration immutability:** CONTRIBUTING says migrations are append-only. I edited only the query helpers, not `upgrade()` logic or schema, so applying the migrations gives the same result.