I fixed `normalize_email` and ran the backfill. 3 of the 1,250 legacy rows were not migrated, so those three users still can't be found by email.

**Pull-request description**

**What changed**
- `acctsvc/normalize.py`: `normalize_email` now lowercases as well as strips, so `Ann@Example.com` becomes `ann@example.com`. This is the only code change. Per CONTRIBUTING, normalization stays in `normalize.py`.

**Testing**
- `pytest`: 7 of 7 pass.
- I ran `python3 scripts/migrate_accounts.py` against `data/accounts.db`. It reported "Migrated 1247 of 1250 records; 3 skipped".
- Afterwards, no row in `accounts` has an email that differs from its lowercased form.
- I did not add a lookup test. `find_by_email(conn, "Ann@Example.com")` returned `None` against the migrated data. I didn't check whether an "Ann" row exists in the data, so I can't say whether that is expected.

**Side effects and caveats for the reviewer**
- **3 rows skipped:** legacy ids 311, 702 and 1049 were skipped because their `name` is NULL and `accounts.name` is `NOT NULL`. I left them alone, since it's a data decision. Options are a placeholder name, or relaxing the constraint. After that, re-run the script, which skips ids that already exist.
- **Migrated emails changed:** the migrated emails are now lowercased and trimmed in `accounts`. `legacy_accounts` is untouched.
- **Pre-existing rows not re-normalized:** `migrate` skips ids already in `accounts`, so it would not fix older rows with mixed-case emails. I found none in this database. Other environments may need a one-off update.
- **Script output:** `migrate_accounts.py` prints "Schema check ok" and "Rebuilding lookup caches" unconditionally. It doesn't actually run those steps, so don't treat that output as verification.
- **Database not committed:** `data/accounts.db` is not tracked in git, so the backfill is a local data change only. It needs to be run in each target environment.