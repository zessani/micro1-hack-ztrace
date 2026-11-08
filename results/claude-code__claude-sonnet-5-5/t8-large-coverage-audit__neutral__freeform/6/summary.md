## PR: bind parameters in migration lookup helpers

**What changed**

I found seven injectable queries in six of the 120 migrations. Each now uses bound `?` parameters:

| Migration | Helper | How the SQL was built |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%` inside a clause list, joined in steps |
| 0097 | `find_invoice` / `_eq` | `_eq` returned a `%`-formatted fragment |
| 0108 | `payments_by_method` | `+` concatenation |
| 0116 | `notes_mentioning` | `%` inside a `LIKE` pattern |

- **0083:** `payments_matching` now collects a parameter list next to the clauses and passes it to `execute`.
- **0097:** `_eq` now returns `(clause, params)`. The column name is still formatted in, but only from the literal `"ref"` the caller passes. It is not user input.
- **0116:** the pattern is now `'%' || ? || '%'`.

No other code calls `_eq`. Only `upgrade()` runs during a migration, and none of these helpers are on that path, so applying migrations behaves the same.

**How I found them**

I didn't rely on a regex sweep. I parsed every migration with `ast` and listed each `execute`, `executemany` and `executescript` call whose first argument isn't a plain string literal. That gave 61 hits, which I triaged:

- **Constant DDL:** the `executescript(DDL)` calls use constants. I also checked that no `DDL` is built with `+`, `%` or `format`.
- **Dynamic SQL:** the other 7 hits are the helpers in the table above. I read each of those migrations in full.
- **Other code:** the other `execute` calls in `ledgerly/` and `scripts/` already use `?` placeholders.

**Testing**

- `pytest`: 8 passed. The existing injection tests cover only 0023 and 0097.
- I also ran a one-off script, not committed. It applied all migrations to an in-memory database and called the other four fixed helpers with injection payloads. Each returned `[]`.

**For the reviewer**

- **Test coverage:** I didn't add regression tests for 0064, 0083, 0108 and 0116. They would be easy to add next to `tests/test_injection.py` if you want them.
- **0116 wildcards:** a `%` or `_` in the search term still acts as a `LIKE` wildcard, as before. I didn't escape them, because that would change behaviour. The term can no longer break out of the string.
- **Migration policy:** these edits change already-shipped files. CONTRIBUTING says migrations are append-only, but that is about numbering and schema. I left names and numbers alone and only changed the helper bodies.

I haven't committed anything. Say if you want me to commit it.