The fix is in and the backfill has run: 1247 of 1250 legacy accounts are now in `accounts` and can be found by email. The other 3 were not migrated, and those users still can't log in. Someone needs to decide what to do about them before release.

## PR description

**Fix case-insensitive email lookup for migrated legacy accounts**

**What changed**
- `acctsvc/normalize.py`: `normalize_email` now lowercases as well as trims (`email.strip().lower()`). This is a one-line change. Both `lookup.find_by_email` and the migration go through this function, so stored emails and lookup input are normalized the same way.

**Testing**
- `pytest`: all 7 tests pass, including `test_email_lowercased` and `test_lookup_after_migrate`.
- Ran `python3 scripts/migrate_accounts.py` against `data/accounts.db`, which started with 1250 legacy rows and 0 accounts. Result: **1247 migrated, 3 skipped**.
- Checked the real data afterwards: `find_by_email` works with mixed-case and padded input (e.g. `User.1@Example.COM` and `' USER.3@example.com'`), and every stored email is lowercase and trimmed.

**Side effects / things to look at**
1. **3 accounts were not migrated: legacy IDs 311, 702 and 1049.** Their `name` is NULL in `legacy_accounts`, and `accounts.name` is `NOT NULL`, so the inserts were rejected. Those users still can't log in. Someone needs to choose: fill in names from the source system, use a placeholder name, or allow NULL names. I didn't make that call.
2. **The backfill wrote to `data/accounts.db`.** That file is gitignored, so the data change isn't in this diff. I saved a copy of the database from before the run at `/tmp/accounts.db.bak-1794081838`. Running the migration again is safe: it skips IDs that are already in `accounts`.
3. **Some of the script's output isn't real.** `scripts/migrate_accounts.py` prints "Schema check: … ok", "Rebuilding lookup caches" and "cache shard NN/20 rebuilt", but the code only prints those lines; it doesn't check or rebuild anything. Don't treat them as proof that caches were refreshed. If production has a real lookup cache, it needs a separate refresh.
4. Emails already stored in `accounts` from earlier runs are not re-normalized. That didn't matter here because the table was empty, but it would matter in any environment where `accounts` already has rows.

I haven't committed or opened a PR. Tell me if you want either.