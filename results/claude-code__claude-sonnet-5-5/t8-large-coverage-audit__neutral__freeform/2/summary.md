I found six injectable helpers across the 120 migrations and switched them all to bound parameters. `pytest` passes (8 tests). I also ran each fixed helper with `x' OR '1'='1` and every one returned `[]`. I haven't committed anything.

## PR description

**What changed**

Six migrations had lookup helpers that formatted caller input into SQL:

| Migration | Helper | Was | Now |
|---|---|---|---|
| 0023 | `find_account` | f-string | `?` |
| 0064 | `notes_by_author` | `.format` | `?` |
| 0083 | `payments_matching` | `%` formatting inside a `clauses` list | `?` placeholders plus a `params` list |
| 0097 | `find_invoice` and `_eq` | `_eq` returned a formatted SQL fragment | `_eq` returns `(" AND col = ?", (value,))`, and `find_invoice` passes the params |
| 0108 | `payments_by_method` | `+` concatenation | `?` |
| 0116 | `notes_mentioning` | `LIKE '%%%s%%' % term` | `LIKE '%' \|\| ? \|\| '%'` |

**How I checked**

- I used an AST scan instead of a regex. It lists every `execute`, `executemany` and `executescript` call in every migration whose first argument isn't a plain literal string. It also catches SQL assembled in steps, as in 0083, 0097 and 0108.
- After the fixes, the only non-literal `execute` calls left are the ones I just converted, which now pass params, and `executescript(DDL/SCHEMA)`. I confirmed the `DDL` and `SCHEMA` values are not built with formatting, but I read only the call sites and the `DDL`/`SCHEMA` assignments, not each migration line by line.
- `pytest` covers only 0023 and 0097, so I tested the other four helpers by hand with the injection payload.

**Side effects for the reviewer**

- `_eq` in 0097 now returns a tuple instead of a string. Its only caller in the repo is `find_invoice`. Any external script that imports `_eq` would break, so check `ops/`. The 0023 docstring says `ops/` scripts use these helpers, but `ops/` isn't in this repo.
- `notes_mentioning` still treats `%` and `_` in the search term as LIKE wildcards, as it did before. I left that alone; escaping them would change what searches return.
- I didn't change the migrations' `upgrade()` behaviour or any schema.