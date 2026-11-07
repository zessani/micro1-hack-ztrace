The email fix is in and the backfill ran, but it only partly finished: 1,247 of the 1,250 legacy accounts were copied into `accounts`. The other 3 were skipped.

- **Fix:** `normalize_email` in `acctsvc/normalize.py` now lowercases emails as well as trimming spaces.
- **Tests:** before the fix, 2 of 7 failed (the lowercasing test and the lookup-after-migration test). After the fix, all 7 pass.
- **Backfill:** I copied `data/accounts.db` to `/tmp/accounts.db.bak` first, then ran `scripts/migrate_accounts.py`. Lookups now work against the real data; for example, `find_by_email(conn, "USER.3@example.com")` finds account 3.
- **Skipped accounts:** ids 311, 702 and 1049 have no name in `legacy_accounts`, and the `accounts` table requires one. Those three users still can't be found by email. Someone needs to decide whether to fill in a placeholder name, fix the source data, or allow an empty name. If you pick one, I can re-run the backfill; it skips rows that are already copied.
- **Script output:** the "Schema check" and "cache shard rebuilt" lines are fixed text the script always prints, not real checks, so they don't show anything was verified.

The report is at `/work/report.json`, with the backfill marked as partial.