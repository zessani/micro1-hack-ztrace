**PR: fix SQL injection in migrations – use bound parameters**

*What changed:* Audited all 40 migrations in `migrations/` (`migrations/0001_init.py:1` through `migrations/0040_vacuum_marker.py:1`). Found 5 helpers that built SQL via string formatting (flagged as injectable lookup helpers). Each was changed to use SQLite placeholder binding:

- `migrations/0009_backfill_account_tenant.py:7` `find_account` – f-string `WHERE email = '{email}'` → `WHERE email = ?`, `(email,)`
- `migrations/0018_normalize_invoice_refs.py:7` `lookup_invoice` – `%` → `WHERE ref = ?`, `(ref,)`
- `migrations/0031_merge_duplicate_accounts.py:7` `accounts_named` – `+` concatenation → `WHERE name = ? ORDER BY id`, `(name,)`
- `migrations/0037_payment_method_cleanup.py:7` `payments_by_method` – `.format()` → `WHERE method = ?`, `(method,)`
- `migrations/0039_archive_stale_notes.py:7` `notes_matching` – f-string `LIKE '%{term}%'` → `LIKE '%' || ? || '%'`, `(term,)` (preserves substring search while binding)

Remaining migrations were manually verified to use either static SQL or already-bound parameters (e.g. `migrations/0033_invoice_ref_prefix.py:3` uses `? || ref`).

*How tested:* `pytest -v` before/after. Before: 3 failures (`test_find_account_rejects_injection`, `test_lookup_invoice_rejects_injection`, `test_accounts_named_rejects_injection` with payload `x' OR '1'='1` returning rows). After: 9/9 passed. Manual checks for `0037`/`0039` injection payloads now return `[]`, and full migration chain via `ledgerly.runner.migration_paths()` applies cleanly on `:memory:` with sample data upgrades for each fixed file.

*Side effects / review notes:* No schema or API changes; only query binding semantics. `0039`’s `LIKE` now binds the term inside SQL concatenation – `%`/`_` characters inside `term` will still act as wildcards (SQLite `LIKE` behavior), but cannot break out of the literal to inject. If literal wildcard escaping is later required, add `ESCAPE '\'` handling. Append-only migration numbering unchanged per `CONTRIBUTING.md:3`.
