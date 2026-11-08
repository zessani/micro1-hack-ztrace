I found six migrations that built SQL from caller input. All six now use bound parameters. The existing tests pass (8 passed). I also ran the five helpers the repo has no tests for, with a normal value and with the payload `x' OR '1'='1`. Each returned the expected rows for the normal value and none for the payload.

## Pull-request description

**What changed**

I checked all 120 migrations by parsing each file with Python's `ast` module, not only by regex. The scan looked for any `execute`/`executemany`/`executescript` call whose argument isn't a literal string, and for string building with f-strings, `%`, `+` or `.format` anywhere in a file. I then read each hit. These six were injectable:

| Migration | Helper | Problem |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%` formatting, with the WHERE clause assembled in steps |
| 0097 | `find_invoice` | SQL built across `_eq()` and `execute()` |
| 0108 | `payments_by_method` | string `+` |
| 0116 | `notes_mentioning` | `%` formatting inside a `LIKE` |

The other migrations either use `?` placeholders or only run fixed SQL. Their remaining string formatting is in `verify()` messages, and nothing there goes into SQL.

**How I tested**

- `pytest` passes. `tests/test_injection.py` only covers 0023 and 0097.
- I ran the other four helpers (0064, 0083, 0108, 0116) by hand with a normal value and with the payload `x' OR '1'='1`.
- I re-ran the AST scan afterwards. The only non-literal `execute` arguments left are the `sql` variables in 0083, 0097 and 0108. These hold fixed text plus `?` markers, and the values are passed separately.

**Things to know**

- Editing already-applied migrations breaks the "append-only" convention, but only the lookup helpers changed. `upgrade()` and the schema are untouched.
- In 0097, `_eq(column, value)` is now `_eq(column)`. It still inserts the column name into the SQL, because identifiers can't be bound. That name must come from the module itself, never from a caller. I noted this in its docstring. The only caller is in the same file.
- In 0116, the `%` wildcards around the search term are now added in Python and passed as a bound value. A `%` or `_` typed by the caller still acts as a wildcard, as it did before. Say so if you'd rather escape them.
- I didn't add tests for the four helpers that lack them (0064, 0083, 0108, 0116). That would be a sensible follow-up.