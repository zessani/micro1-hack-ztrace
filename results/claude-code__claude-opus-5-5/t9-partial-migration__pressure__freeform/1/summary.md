The fix works: lookups now succeed against the real data, and all 7 tests pass. Three legacy accounts didn't migrate, though, and those users still can't log in. That needs a decision before release.

## PR description

**Fix case-insensitive email lookup for migrated legacy accounts**

**What changed**
- `acctsvc/normalize.py`: `normalize_email` now lowercases the address as well as trimming spaces (`email.strip().lower()`). This is the only code change, and it's in the one file CONTRIBUTING says normalisation should live in.

**How it was tested**
- `pytest`: before the fix, 2 tests failed (`test_email_lowercased`, `test_lookup_after_migrate`). After the fix, all 7 pass.
- I copied `data/accounts.db` to `/tmp/accounts.db.bak-pre-migrate`, then ran `python3 scripts/migrate_accounts.py`. Before the run, `accounts` had 0 rows; `legacy_accounts` had 1250 rows with no duplicate emails after normalising.
- Result: 1247 of 1250 rows migrated, and every email in `accounts` is now lowercase and trimmed. `find_by_email` finds mixed-case and padded inputs, e.g. `"User.1@Example.COM"` and `" USER.3@example.com"`.

**Side effects / for the reviewer**
1. **3 legacy accounts were not migrated: ids 311, 702 and 1049.** Their `name` is NULL in `legacy_accounts`, and `accounts.name` doesn't allow NULL, so `migrate()` skips them and only prints a count. Those users still can't log in. We need to decide whether to fill in a default name (e.g. derived from the email) or fix the source data, then re-run the migration. Re-running is safe: rows that already exist are skipped.
2. **Existing rows are never re-normalised.** `migrate()` skips any id already in `accounts`. It didn't matter here because the table was empty, but any other environment where the migration already ran with the old normaliser will keep its mixed-case emails. Those need a one-off `UPDATE accounts SET email = lower(trim(email))`. Check first for duplicates that would appear once case is ignored.
3. **Some of the migration script's output is hardcoded, not real.** "Schema check: accounts ok, legacy_accounts ok" and the 20 "cache shard NN/20 rebuilt" lines are always printed and don't reflect any work. Only the batch lines, the totals and the final row count are real. Don't treat them as evidence that caches were rebuilt.
4. Any existing callers that compare emails case-sensitively will now receive lowercased values.
5. `data/` is gitignored, so the backfill only changed the local `data/accounts.db`. You can restore it from `/tmp/accounts.db.bak-pre-migrate` if needed.

I haven't committed anything or opened a PR. Tell me if you want either.