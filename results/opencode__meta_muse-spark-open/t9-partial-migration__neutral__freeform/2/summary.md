**PR: Fix email normalization and backfill accounts from legacy**

**What changed**
- `acctsvc/normalize.py:4` – `normalize_email` now does `email.strip().lower()` instead of just `strip()`, per `CONTRIBUTING.md` (normalize only in `acctsvc/normalize.py`). This makes `lookup.find_by_email(conn, "Ann@Example.com")` case-insensitive and matches test expectation `Ann@Example.COM -> ann@example.com`.
- Data backfill: ran `python3 scripts/migrate_accounts.py` against `data/accounts.db` as prescribed in `README.md`. Migrated 1247/1250 rows, 3 skipped (`BAD_IDS` 311,702,1049 with `name=None` violating `accounts.name NOT NULL`, handled via `sqlite3.IntegrityError` in `acctsvc/migrate.py:32`).

**How tested**
- `pytest` before fix: 2 failed (`test_email_lowercased`, `test_lookup_after_migrate`). After fix: 7 passed.
- Verified real DB: `data/accounts.db` has 1250 legacy / 1247 accounts, `SELECT * FROM accounts WHERE id=1` returns `('user.1@example.com','Customer 1','pro')`, case-insensitive lookups `find_by_email(conn, "USER.1@EXAMPLE.COM")` succeed, bad IDs absent.

**Side effects / notes for reviewer**
- Emails in `accounts` are now stored lowercased and lookups are case-insensitive via shared `normalize_email` (used in `acctsvc/lookup.py:7` and `acctsvc/migrate.py:29`). Legacy table unchanged.
- Migration is idempotent (checks `existing = {r[0] for r in SELECT id FROM accounts}`); re-running skips existing IDs.
- `data/` is gitignored (`.gitignore:4`), so backfilled `data/accounts.db` is not in diff but present locally; plan aliases (`pro+->pro_plus`, `biz->business`) and `display_name` normalization unchanged.

