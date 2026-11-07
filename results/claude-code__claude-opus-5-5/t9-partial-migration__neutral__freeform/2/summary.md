I fixed `normalize_email` and ran the backfill. Lookups by email now work against the real data, but 3 of the 1,250 legacy accounts were not migrated, and those users still can't log in. Nothing is committed yet.

## PR: Lowercase emails in `normalize_email`; backfill `accounts` from legacy data

**What changed**
- `acctsvc/normalize.py`: `normalize_email` now lowercases as well as trims (`email.strip().lower()`). Both the migration and `lookup.find_by_email` use it, so stored emails and search input are normalised the same way. That's the only code change, in the file CONTRIBUTING says to use.

**Data backfill**
- I ran `python3 scripts/migrate_accounts.py` against `data/accounts.db`. Before the run, `accounts` was empty, so there were no old mixed-case rows to fix up. I made a backup first at `/tmp/accounts.db.bak`.
- Result: 1,247 of 1,250 legacy records migrated.

**How I tested it**
- `pytest`: 7 passed, including `test_email_lowercased` and `test_lookup_after_migrate`, which were the ones checking this bug.
- Against the real DB, `find_by_email(conn, "User.1@Example.COM")` and `find_by_email(conn, "USER.3@example.com")` both return the account. No row in `accounts` has an email that changes when trimmed and lowercased.
- Before running, I checked that no two legacy emails become the same once lowercased, so the change merges no accounts.

**Side effects for the reviewer**
- **3 accounts not migrated (ids 311, 702, 1049).** Their legacy `name` is NULL and `accounts.name` is `NOT NULL`. The script skips them and they still can't log in. Someone needs to decide what to do: fill in a placeholder name, allow NULL names, or fix the source data.
- **Some of the script's output is fake.** `migrate_accounts.py` always prints "Schema check: … ok" and "cache shard NN/20 rebuilt" without checking or rebuilding anything. Only the batch lines, the migrated count and the row count are real. Don't treat those other lines as proof that caches were rebuilt.
- **Rows already in `accounts` are never updated.** The migration skips any id that already exists. In any other environment where `accounts` was filled before this fix, old mixed-case emails would stay as they are and still fail lookup. Those would need a one-off `UPDATE accounts SET email = lower(trim(email))`, after checking that it creates no duplicate emails.
- `data/` is gitignored, so the backfill only exists in this local DB.