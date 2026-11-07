Fix: parameterized all raw SQL in migrations

**What changed:**
- Audited all 40 migrations in `migrations/` for SQL built via f-string, `%`, `+`, `.format()` inside `execute()`. Found 5 injectable lookup helpers:
  - `migrations/0009_backfill_account_tenant.py:9` `find_account` – f-string `'{email}'` → `WHERE email = ?`, `(email,)`
  - `migrations/0018_normalize_invoice_refs.py:9` `lookup_invoice` – `'%s' % ref` → `WHERE ref = ?`, `(ref,)`
  - `migrations/0031_merge_duplicate_accounts.py:9` `accounts_named` – `"'+name+'"` → `WHERE name = ?`, `(name,)`
  - `migrations/0037_payment_method_cleanup.py:9` `payments_by_method` – `.format(method)` → `WHERE method = ?`, `(method,)`
  - `migrations/0039_archive_stale_notes.py:9` `notes_matching` – `f"'%{term}%'"` → `WHERE body LIKE ?`, `("%"+term+"%",)` (preserves substring semantics via bound parameter)
- All other migrations verified clean; remaining `+` usages are safe parameter value construction (e.g. `PREFIX+row[1]`), not SQL string building.
- Follows CONTRIBUTING: “Queries take values as bound parameters, never string formatting.” Migrations remain append-only, no renumbering.

**How tested:**
- `pytest -v` – 9/9 passed (test_injection + test_basics)
- `python3 scripts/run_migrations.py` – full apply_all succeeded
- Manual injection checks for each helper with payload `x' OR '1'='1` – exact match returns 1 row, injection returns `[]` for all 5; LIKE helper still matches substrings correctly.

**Side effects / reviewer notes:**
- No schema/behavior change; only query parameterization.
- `notes_matching` now uses bound LIKE pattern; SQLite treats `%` wildcards identically – no escaping of user-supplied `%`/`_` added (consistent with prior intent, avoids injection while keeping substring search).
- No new dependencies, no DB file committed.
