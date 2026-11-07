**PR description**

**What changed:** I read through the migrations for SQL built from input and found six unsafe lookup helpers. Each now uses bound parameters.
- `0023` `find_account`: the f-string is now `?`.
- `0064` `notes_by_author`: `.format` is now `?`.
- `0083` `payments_matching`: the clauses are built as `method = ?` and `currency = ?`, with a `params` list passed to `execute`.
- `0097` `find_invoice` and `_eq`: `_eq` now returns `(clause, params)`. Its only caller is `find_invoice`.
- `0108` `payments_by_method`: the string concatenation is now `?`.
- `0116` `notes_mentioning`: `LIKE '%%%s%%' % term` is now `LIKE ?`, with the `%` wildcards added in Python.

Every other `execute` call in the 120 migrations is either a literal or already parameterized. I found the six by listing every `execute` call whose argument wasn't a plain literal. That list included the helpers that build SQL in steps (`0083`, `0097`, `0108`). I read those helpers and the multi-line calls rather than relying on the grep alone.

**Testing:**
- `pytest` passes (8 tests), including the existing injection tests for `0023` and `0097`.
- I also ran the payload `x' OR '1'='1` by hand against `0023`, `0064`, `0083`, `0108` and `0116`. Each returned `[]`.
- I didn't add new tests.

**Side effects for the reviewer:**
- `_eq` in `0097` now returns a tuple instead of a string. Nothing else in the repo imports it, but any external ops script that does would break.
- `0116` search now treats a `%` or `_` in the search term as a SQL wildcard, because I didn't add `ESCAPE`. The old code did the same, since the term was spliced into the pattern. Escaping them would be a separate behaviour change.
- No schema or data changes, and the migrations weren't renumbered.