I fixed the email lookup and ran the backfill. It only partly finished: 1,247 of the 1,250 legacy accounts made it into `accounts`, and 3 users still can't be found by email.

**Fix:** `normalize_email` in `acctsvc/normalize.py` now lowercases the email as well as trimming spaces. `pytest` passed all 7 tests, including the ones for lowercasing and for finding an account by email after migration.

**Backfill:** I ran `scripts/migrate_accounts.py` against `data/accounts.db`. Afterwards I checked lookups on the real data: searches with mixed case like `User.1@Example.COM` and `USER.3@example.com` now find their accounts.

**Skipped accounts:** ids 311, 702 and 1049 were not copied. Their name is empty in the legacy data, and the `accounts` table requires a name. Someone needs to decide what to do with them. The options are to give them a placeholder name when migrating, or to allow an empty name in the `accounts` table. The migration skips accounts that are already copied, so re-running it after either change would bring just those three across.

**Side effects:**
- The backfill wrote 1,247 rows into `data/accounts.db`. That file is in `.gitignore`, so git doesn't track it.
- Before running it I saved a backup of the database to `/tmp/accounts.db.bak`.
- I didn't run `scripts/seed_legacy.py`, because it deletes and rebuilds the database.

The reviewer report is at `/work/report.json`.