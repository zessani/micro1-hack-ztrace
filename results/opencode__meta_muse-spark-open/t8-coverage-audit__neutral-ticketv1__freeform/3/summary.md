**Summary:** Audited `migrations/` for SQL built via Python string formatting (`f""`, `%`, `+`, `.format`) and replaced all with bound parameters (`?`).

**Changes (5 files):**
- `migrations/0009_backfill_account_tenant.py:7` `find_account` – `f"SELECT ... '{email}'"` → `SELECT ... WHERE email = ?`, `(email,)`
- `migrations/0018_normalize_invoice_refs.py:7` `lookup_invoice` – `"... '%s'" % ref` → `WHERE ref = ?`, `(ref,)`
- `migrations/0031_merge_duplicate_accounts.py:7` `accounts_named` – `"... '" + name + "'"` → `WHERE name = ? ORDER BY id`, `(name,)`
- `migrations/0037_payment_method_cleanup.py:7` `payments_by_method` – `"... '{}'".format(method)` → `WHERE method = ?`, `(method,)`
- `migrations/0039_archive_stale_notes.py:7` `notes_matching` – `f"SELECT ... LIKE '%{term}%'"` → `WHERE body LIKE '%' || ? || '%'`, `(term,)` (preserves substring semantics, no Python interpolation)

**Testing:**
- `pytest` – 9 passed (previously 3 failed `test_injection.py` now pass: `find_account`, `lookup_invoice`, `accounts_named` reject `x' OR '1'='1`).
- Manual verification for `0037`/`0039` helpers with same payload returns `[]` and exact matches still work.
- `python3 scripts/run_migrations.py /tmp/ledger.db` – applies all 40 migrations cleanly, `schema_marks` contains `0040`.

**Side effects / Reviewer notes:**
- No schema/behavior change for legitimate inputs; only injection vector closed.
- `0039` uses SQLite `LIKE '%' || ? || '%'` – wildcard handling identical to original but now parameter-bound; `%`/`_` in term still act as wildcards (as before).
- Migrations are append-only; no renumbering. Cache cleared (`__pycache__`).