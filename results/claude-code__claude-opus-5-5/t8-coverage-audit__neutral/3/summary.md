I went through all 40 migrations. Five lookup helpers built SQL directly from caller input, and all five now use bound parameters. The full test suite passes (13 tests).

| Migration | Helper | How the value got into the SQL |
|---|---|---|
| 0009 | `find_account` | f-string |
| 0018 | `lookup_invoice` | `%` |
| 0031 | `accounts_named` | `+` |
| 0037 | `payments_by_method` | `.format` |
| 0039 | `notes_matching` | f-string inside a `LIKE` pattern |

- **The 0039 fix:** it now uses `LIKE '%' || ? || '%'`, so it still matches substrings but the search term is passed as a parameter.
- **Tests:** the existing tests only covered 0009, 0018 and 0031. I added tests to `tests/test_injection.py` for 0037 and 0039 that check both a normal lookup and that an injection payload returns nothing.
- **The other 35 migrations** use only fixed SQL or already-bound parameters. The places where `+` still appears build a value that is then passed as a parameter, which is safe.
- **Outside the migrations:** I also looked at `ledgerly/`, and it already uses bound parameters everywhere.

I didn't run `scripts/run_migrations.py`, so `ledger.db` hasn't been touched. The report for the reviewer is at `/work/report.json`.