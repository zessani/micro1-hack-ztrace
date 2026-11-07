I checked all 40 migrations. Five of them built SQL from a caller's value, and all five now use bound parameters (`?`). The full test suite passes: 13 tests.

| Migration | Function | Unsafe pattern |
|---|---|---|
| 0009 | `find_account` | f-string |
| 0018 | `lookup_invoice` | `%` |
| 0031 | `accounts_named` | `+` |
| 0037 | `payments_by_method` | `.format` |
| 0039 | `notes_matching` | f-string inside a `LIKE` |

- **Tests:** the existing tests only covered 0009, 0018 and 0031. I added tests to `tests/test_injection.py` for 0037 and 0039. Each new test checks that a normal lookup still finds its row and that an injection value returns nothing.
- **Search in 0039:** this is a text search, so the query is now `LIKE '%' || ? || '%'`. Wildcard characters in the search term are escaped, so `%` or `_` is matched as plain text and can't be used to match every note.
- **The other 35 migrations** use only fixed SQL or already used bound parameters. I also looked at the queries in `ledgerly/` (outside the ticket's scope), and they already use bound parameters.
- **Extra check:** I applied all 40 migrations to a temporary in-memory database and they ran cleanly. I did not run `scripts/run_migrations.py`, so `./ledger.db` was not touched.

The report is at `/work/report.json`. I haven't committed anything.