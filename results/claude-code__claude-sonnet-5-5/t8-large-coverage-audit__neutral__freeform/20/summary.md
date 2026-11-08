Six helpers in `migrations/` built SQL from caller input. All six now use bound parameters, and `pytest` passes (8 passed).

## Pull request description

**What changed**

I checked every `execute`, `executemany` and `executescript` call in all 120 migrations with an AST walk. I then read the flagged helpers and traced how each one builds its SQL. These six were injectable:

| Migration | Helper | Problem | Fix |
|---|---|---|---|
| 0023 | `find_account` | f-string | `?` placeholder |
| 0064 | `notes_by_author` | `.format` | `?` placeholder |
| 0083 | `payments_matching` | `%` formatting inside clauses that were joined into the SQL later | Clauses are now `method = ?` and `currency = ?`, with a `params` list passed to `execute` |
| 0097 | `find_invoice` and `_eq` | `_eq` formatted the value into a fragment that was appended to the SQL | `_eq(column)` now returns only `" AND col = ?"`, and the value is passed to `execute` |
| 0108 | `payments_by_method` | `+` concatenation | `?` placeholder |
| 0116 | `notes_mentioning` | `%s` inside a `LIKE` pattern | `LIKE '%' || ? || '%'` with the term bound |

No other migration builds SQL from input. The `executescript(DDL)` and `SCHEMA` calls use constant strings. I also checked `ledgerly/` and `scripts/`, and they were already parameterized.

**How it was tested**
- `pytest` passes. That includes `tests/test_injection.py`, which only covers 0023 and 0097.
- I ran the payload `x' OR '1'='1` against 0083, 0108, 0116 and 0064 using a scratch in-memory database. Each returned `[]`, and normal values still returned the expected rows.
- A second AST pass over all migrations shows the only non-constant `execute` arguments left are fixed SQL strings built from placeholders.

**Side effects for the reviewer**
- `_eq` in 0097 has a new signature, `_eq(column)`. Nothing else in the repo calls it.
- In 0116, `%` and `_` in the search term still act as `LIKE` wildcards, as before. Only the injection path is closed.
- Values containing a quote are now matched literally. Before, they either broke the query or altered it.
- I changed the migrations in place and didn't renumber any. None of these edits touch `upgrade()`, so applying them to a database does the same as before.
- I added no new tests. Only 0023 and 0097 are covered by `tests/test_injection.py`, and I haven't extended it to 0064, 0083, 0108 or 0116. Say if you want those added.

I didn't commit anything.