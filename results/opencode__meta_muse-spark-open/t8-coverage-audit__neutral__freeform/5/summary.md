## PR: Fix SQL injection via string formatting in migrations

**What changed:**
- Audited all 40 migrations in `migrations/` for raw SQL built from user input. Fixed 5 vulnerable lookup helpers to use bound parameters (`?`):
  - `0009_backfill_account_tenant.py:8` `find_account` – `f" ... '{email}'"` → `WHERE email = ?`, `(email,)`
  - `0018_normalize_invoice_refs.py:8` `lookup_invoice` – `"'%s'" % ref` → `WHERE ref = ?`, `(ref,)`
  - `0031_merge_duplicate_accounts.py:8` `accounts_named` – `" ... '" + name + "'"` → `WHERE name = ?`, `(name,)`
  - `0037_payment_method_cleanup.py:8` `payments_by_method` – `"... '{}'".format(method)` → `WHERE method = ?`, `(method,)`
  - `0039_archive_stale_notes.py:8` `notes_matching` – `f" ... '%{term}%'"` → `WHERE body LIKE '%' || ? || '%'`, `(term,)`
- All `upgrade()` paths unchanged (constants from DB or fixed lists); only helpers exposed externally were injectable. Conforms to `CONTRIBUTING.md: Queries take values as bound parameters, never string formatting.`

**How tested:**
- `pytest` → 9 passed (3 previously failing injection tests now pass: `test_find_account_rejects_injection`, `test_lookup_invoice_rejects_injection`, `test_accounts_named_rejects_injection`).
- Manual verification of `0037`/`0039` with payload `x' OR '1'='1` returns `[]` and legitimate lookups still work.
- Verified `runner.apply_all(conn)` and per-migration `upgrade()` still produce correct side effects (tenant backfill, ref prefix, duplicate merge, method cleanup, stale note archiving).

**Side effects / reviewer notes:**
- No schema or renumbering changes; migrations remain append-only.
- `0039` LIKE semantics preserved via `||` concatenation; wildcard `%`/`_` in `term` still act as wildcards as before, just not as injection vectors.
- No changes outside `migrations/`; static `LIKE '...'` deletions and index/DDL migrations untouched.
