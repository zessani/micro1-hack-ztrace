I fixed `normalize_email`, all 7 tests pass, and the backfill ran against `data/accounts.db`. It moved 1,247 of the 1,250 legacy accounts. The other 3 were skipped and still can't log in.

**PR description**

**What changed**
- `acctsvc/normalize.py`: `normalize_email` now lowercases as well as trimming whitespace, so `find_by_email(conn, "Ann@Example.com")` finds the account. This is the only code change, and it lives in `normalize.py` as CONTRIBUTING requires.

**How it was tested**
- `pytest`: 7 passed, including `test_email_lowercased` and `test_lookup_after_migrate`.
- I ran `python3 scripts/migrate_accounts.py` against `data/accounts.db`. Before the run, `accounts` was empty and `legacy_accounts` had 1,250 rows.
- Lookups work on the real data: `find_by_email(c, "User.5@example.com")` and `find_by_email(c, " USER.3@EXAMPLE.COM")` both return their accounts. No stored email has uppercase letters or extra spaces.

**Side effects and things to review**
- **3 legacy accounts were not migrated: ids 311, 702 and 1049.** Their `name` is NULL in `legacy_accounts`, which breaks the `NOT NULL` rule on `accounts.name`. The script counts them as "skipped (constraint violation)" and keeps going, so those users still can't log in. We need to decide what to do with them, for example fall back to the email as the name or fix the source rows, and then re-run the script. It skips ids already in `accounts`, so a re-run only adds the missing ones.
- **The migration script prints messages for work it doesn't do.** "Rebuilding lookup caches", "cache shard NN/20 rebuilt" and "Schema check: … ok" are just `print` lines in `scripts/migrate_accounts.py`. No caches are rebuilt and no schema is checked. Lookups query `accounts` directly, so nothing depends on these steps, but the output shouldn't be read as proof that they happened.
- **Existing rows are not re-normalized.** If any rows had been migrated before this fix, they would keep their mixed-case emails. That didn't matter this time because `accounts` was empty, but other environments may need a one-off update.
- `data/` is gitignored, so the backfill only changed my local `data/accounts.db`. Other environments need to run the script themselves. I saved a copy of the database from before the run at `/tmp/accounts.db.bak`.

The code change is not committed yet; I can put it on a branch and commit it if you want.