**PR: use bound parameters in migration lookup helpers**

**What changed**

I read through all 120 files in `migrations/`. Six of them had helpers that built SQL from caller-supplied values. I changed each to use `?` placeholders:

| Migration | Helper | Was |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%` clauses joined in steps; now builds a clause list and a params list |
| 0097 | `find_invoice` | `_eq()` helper that formatted values in; I removed `_eq()` and its only caller was `find_invoice` |
| 0108 | `payments_by_method` | `+` concatenation |
| 0116 | `notes_mentioning` | `%` inside a `LIKE` pattern; now `'%' \|\| ? \|\| '%'` |

**How I checked for others**

- I didn't rely on a regex. I used a script that parses every migration and lists each `execute*()` call whose first argument isn't a plain string literal.
- Besides these six, the only non-literal calls are `executescript(DDL)` and `executescript(SCHEMA)`. Those constants are fixed, and I confirmed they don't use formatting.
- All the other helpers already used bound parameters.

**Testing**

- `pytest` passes (8 tests), including `tests/test_injection.py`.
- That file only covers 0023 and 0097. I also ran the injection payload `x' OR '1'='1` by hand against 0064, 0083, 0108 and 0116, using throwaway in-memory tables. Each returns no rows. The normal lookups still return the expected rows.
- I didn't add tests for those four, so you may want to.

**Side effects for the reviewer**

- Helpers now return the same results for legitimate input. The only change is that quotes in input are treated as data instead of SQL.
- In 0116, `%` and `_` typed by a caller still act as `LIKE` wildcards, as before. Escaping them would change search behaviour, so I left that alone.
- `upgrade()` logic and schema are untouched. The edits are limited to the helper functions, so already-applied migrations aren't affected, and I didn't renumber anything.
- `_eq` in 0097 is gone. It was private, and nothing else in the repo referenced it.