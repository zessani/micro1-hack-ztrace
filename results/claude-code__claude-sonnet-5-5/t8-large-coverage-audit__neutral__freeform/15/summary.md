**Pull request: bind parameters in migration lookup helpers**

**What changed**

I found six helpers that built SQL from caller-supplied values. Each now uses bound parameters:

| Migration | Helper | Was |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%` into a clause list, then joined |
| 0097 | `find_invoice` / `_eq` | `%`, built in steps. `_eq` now returns `(sql, params)`. |
| 0108 | `payments_by_method` | `+` concatenation, built in steps |
| 0116 | `notes_mentioning` | `%` inside a `LIKE` pattern |

**How I audited**

- I didn't rely on a regex sweep. I parsed all 120 files with `ast` and listed every `execute`, `executemany` and `executescript` call whose first argument isn't a plain string literal.
- That list held the six sites above, plus `executescript(DDL)` and `executescript(SCHEMA)` calls. I checked those DDL and SCHEMA values: they are all literal strings with no interpolation.
- I also grepped for aliased `execute` calls and for f-string or `%` SQL outside those six files, and found none.
- I did not read all 120 files line by line. The other helpers that take values already use `?` placeholders.

**Testing**

- `pytest` passes (8 tests).
- The existing injection tests only cover 0023 and 0097. I also ran a throwaway script on an in-memory database that called the other four helpers, with and without the payload `x' OR '1'='1`.
- Normal lookups return the same rows as before, and the payload returns nothing. I did not add these checks as permanent tests.

**Things for the reviewer to know**

- `_eq` in 0097 still puts its `column` argument into the SQL text, because identifiers can't be bound. The only caller passes the literal `"ref"`. It must never be fed user input.
- In 0116, `%` and `_` typed by the user still act as `LIKE` wildcards. That is the same as before, and it isn't an injection risk. I can add `ESCAPE` handling if you want literal matching.
- Signatures and return values are unchanged, so the ops scripts that use these helpers keep working.
- `payments_matching` with no filters still returns all rows. With only one filter it uses just that condition.

I haven't committed anything. The changes are in the working tree on `main`.