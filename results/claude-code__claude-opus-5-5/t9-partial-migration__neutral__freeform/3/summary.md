I fixed `normalize_email` and ran the backfill against `data/accounts.db`. Mixed-case lookups now work, but 3 of the 1,250 legacy accounts were not migrated, so those users still can't log in.

## PR description

**Fix case-insensitive email lookup for migrated legacy accounts**

**What changed**
- `acctsvc/normalize.py`: `normalize_email` now lowercases as well as trimming whitespace. CONTRIBUTING says this is the only place to normalise identifiers. Lookups and the migration both use this function, so stored emails and query emails are now in the same form.

**How it was tested**
- `pytest`: all 7 tests pass, including `test_email_lowercased` and `test_lookup_after_migrate`.
- Ran `python3 scripts/migrate_accounts.py` on `data/accounts.db`. It copied 1,247 of 1,250 rows into `accounts`, which was empty before.
- Lookups on the real data work: `find_by_email(conn, "USER.5@example.com")` returns account 5, and 0 stored emails have uppercase letters or surrounding spaces.

**Side effects / reviewer notes**
- **3 accounts were skipped:** legacy ids 311, 702 and 1049 have no `name`, and `accounts.name` is `NOT NULL`. Someone needs to decide what to do with them, either fill in a placeholder name or allow nulls, and then re-run the script. It skips rows already migrated, so re-running is safe.
- **The database was changed:** `data/` is gitignored, so none of this is in the diff. I saved a copy of the database from before the migration at `data/accounts.db.bak-pre-migrate`.
- **The script's "Rebuilding lookup caches … shard 01/20 rebuilt" lines are only print statements.** No cache is actually rebuilt. Lookups go straight to SQLite, so it doesn't matter here, but the output is misleading.
- I didn't run `scripts/seed_legacy.py`, because it deletes and rebuilds `data/accounts.db`.

The change isn't committed; I can put it on a branch and commit it if you want.