I fixed all five injectable migrations. `pytest` passes (9 tests, including the injection tests), and `scripts/run_migrations.py` applies all 40 migrations cleanly.

## PR description

**Fix SQL injection in migration lookup helpers**

**What changed**
I read all 40 files in `migrations/`. Five built SQL by formatting caller-supplied values into the query string, and I switched each to bound parameters:

| Migration | Helper | Was | Now |
|---|---|---|---|
| 0009 | `find_account(email)` | f-string | `email = ?` |
| 0018 | `lookup_invoice(ref)` | `%` formatting | `ref = ?` |
| 0031 | `accounts_named(name)` | `+` concatenation | `name = ?` |
| 0037 | `payments_by_method(method)` | `.format` | `method = ?` |
| 0039 | `notes_matching(term)` | f-string inside `LIKE` | `LIKE '%' \|\| ? \|\| '%'` |

The other 35 migrations are static DDL or constant statements, or already use `?` parameters. A few contain literals such as `LIKE '%@test.invalid'`, but none of them take input. I also checked `ledgerly/` and found no other string-built SQL.

**Testing**
- `pytest` passes. It covers exact-match and injection-payload cases for 0009, 0018 and 0031.
- `scripts/run_migrations.py` applies all 40 migrations cleanly.
- 0037 and 0039 have no dedicated injection tests. The same change is covered only by the full migration run. Say if you want tests added.

**Side effects**
- Query results for normal values are the same, and no migration was renumbered or added.
- In 0039, `%` and `_` inside `term` still act as `LIKE` wildcards, as before. The current marker values (`obsolete`, `superseded`) contain neither, so there's no change in behaviour.