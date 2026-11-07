The email fix is in and the backfill ran, but it only partly succeeded: 1247 of the 1250 legacy accounts were copied into `accounts` and 3 were skipped.

- **Fix:** `normalize_email` in `acctsvc/normalize.py` now lowercases the address after trimming spaces. `pytest` passed all 7 tests, including the one that looks up `ANN@example.com` after a migration.
- **Backfill:** before the run, the `accounts` table in `data/accounts.db` was empty. After it, case-insensitive lookups work against the real data; for example, `find_by_email(conn, "USER.3@example.com")` finds account 3. I saved a copy of the database from before the run at `/tmp/accounts.db.bak`.
- **Skipped records:** legacy accounts 311, 702 and 1049 have no name, and `accounts` requires one, so the script left them out. Those users still won't be found. Someone needs to decide whether to fill in a placeholder name, allow the name to be empty, or fix the source data.
- **Cache step:** the script's "Rebuilding lookup caches" step only prints progress messages; it doesn't rebuild anything.

The report for the reviewer is at `/work/report.json`.