## PR description

**Fix SQL injection in migration lookup helpers**

**What changed**
I read all 120 files in `migrations/`. Six helpers built SQL from caller input, and I switched each to bound parameters:

| Migration | Helper | Was |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%` in a clause list, joined into `sql` |
| 0097 | `find_invoice` | `_eq()` helper that used `%`; I removed it, since nothing else used it |
| 0108 | `payments_by_method` | `+` concatenation |
| 0116 | `notes_mentioning` | `%` inside a `LIKE` pattern |

The other 114 migrations were already safe. Their `execute()` calls use constant SQL with `?` parameters, and the `DDL`/`SCHEMA` constants passed to `executescript()` are literals.

**How I found them**
A regex sweep missed cases last time, so I used a script that parses each file's AST. It flagged every `execute`, `executemany` and `executescript` call whose SQL isn't a literal string. That caught the helpers that build the SQL in steps (0083, 0097, 0108). I fixed those and re-ran the script. The only remaining flags are the `executescript(DDL)` calls and the now-parameterized calls.

**Testing**
- `pytest` passes: 10 tests, 2 existing and 2 new in `tests/test_injection.py`.
- The new tests give the 0064, 0116, 0083 and 0108 helpers both a normal input and an injection payload. They show the payload no longer matches rows.
- 0023 and 0097 already had tests like this.

**Side effects for the reviewer**
- **Edited migrations:** CONTRIBUTING says migrations are append-only. I edited only the helper functions, not `upgrade()` or the schema, so applying the migrations gives the same result. The edits do change the files, so any checksum-based tracking would see a difference.
- **`LIKE` wildcards:** in 0116, `notes_mentioning` now binds the term as `'%' || ? || '%'`. It still treats `%` and `_` in the term as wildcards, as before. Escaping them would change search behavior, so I didn't.
- **Dead helper:** `_eq` in 0097 is gone. Nothing else in the repo referenced it.