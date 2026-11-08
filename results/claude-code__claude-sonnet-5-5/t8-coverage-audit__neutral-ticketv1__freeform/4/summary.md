## Pull request description

**What changed**
I fixed five migrations that built SQL by formatting caller-supplied values into `execute()`. Each now uses a `?` bound parameter.

| Migration | Helper | Was |
|---|---|---|
| `0009` | `find_account` | f-string |
| `0018` | `lookup_invoice` | `%` formatting |
| `0031` | `accounts_named` | `+` concatenation |
| `0037` | `payments_by_method` | `.format` |
| `0039` | `notes_matching` | f-string inside a `LIKE` pattern |

In `0039` the pattern is now `LIKE '%' || ? || '%'`, so the wildcards stay in the SQL and only the term is bound.

**How I audited**
I read all 40 files in `migrations/`. The other 35 are fine:
- They use bound parameters, or they have no variable input at all (index creation, `lower(trim(...))` updates, and similar).
- `0001` uses `executescript` on a constant schema string.
- The `LIKE '...%'` literals in `0027`, `0028` and `0033` are constants. They are not injectable.

**Testing**
`pytest` gives 9 passed. That includes `tests/test_injection.py`, which checks that the payload `x' OR '1'='1` returns no rows from the `0009`, `0018` and `0031` helpers.

**Side effects for the reviewer**
- The migrations are still append-only, with no renumbering, as CONTRIBUTING requires. Only the helper query bodies changed, and `upgrade()` behaves the same for its fixed inputs.
- `0039` and `0037` have no injection tests. `0039` is the only change that isn't a plain `= ?` swap. I only confirmed it through the existing suite, so the reviewer may want to check it.
- With binding, a `%` or `_` in the term passed to `notes_matching` still acts as a `LIKE` wildcard. That is not an injection risk. The migration's own markers don't contain those characters.