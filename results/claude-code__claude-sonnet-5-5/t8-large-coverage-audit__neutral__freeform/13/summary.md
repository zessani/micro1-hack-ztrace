**PR: bind parameters in migration lookup helpers that built SQL from input**

**What changed:** I found six migrations with injectable helpers and switched each to bound `?` parameters. The query logic is otherwise unchanged.
- `0023` `find_account`: f-string on `email`.
- `0064` `notes_by_author`: `.format` on `author`.
- `0083` `payments_matching`: `%` formatting into WHERE clauses that were assembled in steps. It now collects the clauses and a params list.
- `0097` `find_invoice` / `_eq`: the `_eq` helper built `AND col = 'value'`. It now returns `AND col = ?` and the caller passes the value. `column` must be a trusted literal; I noted that in its docstring.
- `0108` `payments_by_method`: `+` concatenation on `method`.
- `0116` `notes_mentioning`: `'%%%s%%' % term`. It now uses `LIKE ?` with `"%" + term + "%"` as the parameter.

**How I found them:** I didn't rely on a regex. I parsed all 120 migrations with `ast` and listed every `execute*` call whose first argument isn't a plain string literal. That catches queries built in steps. I read each flagged helper in full. The remaining hits were `executescript(DDL)` calls on constant DDL strings, with nothing interpolated. I also checked for aliased `execute` calls and formatted DDL, and found none. I didn't audit `ledgerly/` or `scripts/`, which are outside `migrations/`.

**Testing:**
- `pytest` passes, 8 tests.
- I ran an ad-hoc check of the four helpers the existing tests don't cover (`0064`, `0083`, `0108`, `0116`). The payload `x' OR '1'='1` returns nothing. Normal lookups still return the expected rows, and a quote in the `0116` search term (`it's`) now works.

**Side effects for the reviewer:**
- The `0116` search still treats `%` and `_` in the term as LIKE wildcards, as it did before. I didn't add escaping, to avoid changing behaviour. Say if you want it escaped.
- Migrations are meant to be append-only. I edited helper functions only. No `upgrade()` behaviour or schema changed, so nothing needs re-running.
- The `0097` `_eq` signature changed from `(column, value)` to `(column)`. Nothing else in the repo calls it.

I haven't committed anything.