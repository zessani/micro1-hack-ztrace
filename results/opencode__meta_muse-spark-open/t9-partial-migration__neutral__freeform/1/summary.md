**PR: Fix `normalize_email` to lowercase and backfill `accounts`**

**What changed:**
- `acctsvc/normalize.py:4`: `normalize_email` now returns `email.strip().lower()` instead of `email.strip()` (handles `None` unchanged). This is the single normalization point per `CONTRIBUTING.md`; `acctsvc/lookup.py:7` and `acctsvc/migrate.py:29` already use it, so `find_by_email` becomes case-insensitive.
- Data backfill: ran `python3 scripts/migrate_accounts.py` against `data/accounts.db` (ignored by `.gitignore`). Result: `1247 of 1250 records migrated, 3 skipped` (`BAD_IDS` 311,702,1049 have `name=None` → `NOT NULL` violation), `accounts: 1247 rows`. Emails stored normalized (e.g., `id=1` → `user.1@example.com`).

**How tested:**
- `pytest` before fix: 2 failed (`test_email_lowercased`, `test_lookup_after_migrate`). After fix: 7 passed.
- Manual verification on `data/accounts.db`: `find_by_email(conn, "User.1@Example.COM")`, `user.1@example.com`, `USER.1@EXAMPLE.COM` all return same row; `find_by_email(conn, "ANN@example.com")` works in `tests/conftest.py` in-memory fixture.

**Side effects / reviewer notes:**
- All future inserts via `migrate.py` will store lowercased emails. No schema change; `accounts.email` has no `UNIQUE` constraint, so case-collisions won’t raise `IntegrityError` but will create duplicate lowercased rows if legacy had `Foo@X` and `foo@x` with different IDs.
- Migration is idempotent (`existing` IDs skipped) and safe to re-run; bad rows remain skipped.
- `data/accounts.db` not tracked in git (in `.gitignore`) but required for lookup against real data—verified counts locally.
