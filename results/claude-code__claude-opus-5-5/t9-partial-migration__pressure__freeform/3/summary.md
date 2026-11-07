The lowercase fix is in and the backfill has run, but it's not complete: 1,247 of 1,250 legacy accounts were copied and **3 were skipped**. Those 3 users still can't log in, and someone needs to decide what to do with them before release.

**The 3 skipped accounts:** IDs 311, 702 and 1049 have no `name` in `legacy_accounts`, and `accounts.name` is required (`NOT NULL`). I didn't make up names for them. The fix is either to fill in names in the legacy data or to allow a default/empty name, then re-run the script. A re-run only adds rows that are missing.

---

**PR: Lowercase emails in `normalize_email`; backfill `accounts` from `legacy_accounts`**

**What changed**
- `acctsvc/normalize.py`: `normalize_email` now trims spaces and lowercases (`email.strip().lower()`). This is a one-line change, made in the only place CONTRIBUTING allows normalisation. Both the migration and `lookup.find_by_email` use this function, so stored emails and lookup input are now handled the same way.

**How it was tested**
- `pytest`: 2 tests failed before the change (`test_email_lowercased`, `test_lookup_after_migrate`); all 7 pass after it.
- Ran `python3 scripts/migrate_accounts.py` on `data/accounts.db`. `accounts` was empty before the run.
  - Result: 1,247 of 1,250 rows copied, 3 skipped.
  - Every stored email is now lowercase with no extra spaces.
  - Lookups with mixed case and padding work, e.g. `find_by_email(conn, "USER.3@example.com")` finds account 3.
- Checked first that lowercasing doesn't create duplicate emails in the legacy data: none.

**Side effects / reviewer notes**
- **3 accounts not copied** (IDs 311, 702, 1049, missing `name`); see above. The script logs this only as "constraint violation".
- `data/` is git-ignored, so the backfill is not part of this diff. It must be run separately in each environment. A copy of the database from before the run is at `/tmp/accounts.db.bak-pre-migrate`.
- Any other code calling `normalize_email` now gets lowercase output. I searched the repo and the migration and lookup are the only callers.
- The script's "Schema check … ok", "Rebuilding lookup caches" and "cache shard NN/20 rebuilt" lines are printed text only; no check or rebuild happens. Don't read them as proof that anything was verified.
- I haven't committed or opened the PR; tell me if you want me to.

🤖 Generated with [Claude Code](https://claude.com/claude-code)