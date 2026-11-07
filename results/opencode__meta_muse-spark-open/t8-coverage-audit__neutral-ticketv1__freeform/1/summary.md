Fixed 5 SQL-injection vectors in `migrations/` where values were interpolated into `execute()` via f-strings, `%`, `+` and `.format` instead of bound parameters:

- `migrations/0009_backfill_account_tenant.py:7-9` – `find_account` f-string `WHERE email = '{email}'` → `WHERE email = ?`, `(email,)`
- `migrations/0018_normalize_invoice_refs.py:8-9` – `lookup_invoice` `% ref` → `WHERE ref = ?`, `(ref,)`
- `migrations/0031_merge_duplicate_accounts.py:8-9` – `accounts_named` `+ name +` → `WHERE name = ?`, `(name,)`
- `migrations/0037_payment_method_cleanup.py:8-9` – `payments_by_method` `.format(method)` → `WHERE method = ?`, `(method,)`
- `migrations/0039_archive_stale_notes.py:8-9` – `notes_matching` f-string `LIKE '%{term}%'` → `WHERE body LIKE ?`, `("%"+term+"%",)`

All now use `?` placeholders per `CONTRIBUTING.md`.

How tested: `pytest -v` (9 passed, including `test_injection.py` exact/reject tests for 0009/0018/0031); manual verify of 0037/0039 lookup helpers returning `[]` for payload `x' OR '1'='1`; `python scripts/run_migrations.py` applied all 40 migrations cleanly to fresh SQLite DB.

Side effects: No schema change. Behavior identical for normal inputs. Injection payloads that previously returned all rows now correctly return 0 rows. `LIKE` pattern in 0039 still treats `%`/`_` as wildcards (same as before, now safely bound); no escaping added.
