Fixed `normalize_email` and ran the backfill. 3 of the 1,250 legacy records were not migrated. Tests pass (7 passed).

**Pull-request description**

**What changed**
- `acctsvc/normalize.py`: `normalize_email` now lowercases as well as strips, so `lookup.find_by_email(conn, "Ann@Example.com")` matches the stored value. The change is in `normalize.py` only, as CONTRIBUTING requires.
- I ran `scripts/migrate_accounts.py` against `data/accounts.db`, which is not tracked in git. `accounts` went from 0 to 1,247 rows. Every stored email is lowercase, and a spot check of `user.1@example.com` looked right.

**Testing**
- `pytest` passes, including the existing `normalize_email` case/whitespace tests.
- I checked the migrated data directly: no row has `email != lower(email)`.
- I did not run `find_by_email` against the migrated DB with a mixed-case address. It uses the same `normalize_email`, so it should match.

**Reviewer notes**
- **3 records were skipped** with a constraint violation: ids 311, 702 and 1049. All three have `name = NULL`, and `accounts.name` is `NOT NULL`. Those users still can't be found by email. Someone needs to decide on a default name or fix the source data. I didn't guess a fallback.
- `migrate()` skips ids already in `accounts`, so re-running it won't correct rows migrated earlier with the old normalization. The table was empty here, so this didn't matter. Any other environment with a previously populated `accounts` table would need those rows re-normalized.
- Lowercasing could create duplicate emails if the legacy data has addresses that differ only by case. No such collisions showed up in this run.