I found and fixed six injectable helpers, one in each of six migrations. `pytest` passes (8 tests). I also called each fixed helper with `x' OR '1'='1` against a fresh database, and each returned no rows.

**PR description**

**What changed**

I checked all 120 files in `migrations/` with an AST scan instead of a regex. The scan flags any `execute`, `executemany` or `executescript` call whose first argument isn't a plain string literal, so it also catches SQL that is built up in steps. Six calls were flagged. Every other flagged call was `executescript(DDL)` or `executescript(SCHEMA)` with a constant, which is safe.

I then read the flagged calls and fixed all six to use bound parameters:

| Migration | Helper | Previous construction |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%`, built in steps |
| 0097 | `find_invoice` (via `_eq`) | `%`, built in steps |
| 0108 | `payments_by_method` | `+` concatenation |
| 0116 | `notes_mentioning` | `%` inside a `LIKE` |

Details a reviewer may want to check:
- **0083:** it now collects a `params` list alongside the `WHERE` clauses.
- **0097:** `_eq(column, value)` now returns `(sql_fragment, params)`. The column name is still interpolated, but the only caller passes the literal `"ref"`, and the docstring says it must be a trusted identifier.
- **0116:** `LIKE ?` with `ESCAPE '\'`.

Signatures are unchanged, so the `ops/` scripts that call these helpers keep working. I edited existing migration files in place and did not renumber or add any.

**Testing**
- `pytest` passes with 8 tests, including the existing injection tests for 0023 and 0097.
- I ran the injection payload by hand against the other four helpers. I did not add new tests for them.
- I did not run `scripts/ops_check.py`.

**Side effects**
- **0116 search behaviour:** `%` and `_` in the search term are now matched literally. Before, they acted as wildcards, so a term like `50%` used to match more than it should. This is intended, but it is a change in behaviour.
- **Scope:** I scanned only `migrations/`. A quick grep of `ledgerly/` found no formatted SQL.
- **Scanner limits:** the scan only recognises calls named `execute`, `executemany` and `executescript`. I grepped for aliased `execute` calls and for dynamically built `DDL` strings and found none.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>