**Pull Request: Fix SQL injection in migrations via bound parameters**

**What changed:**
Audited all 40 migrations in `migrations/` for raw SQL built from user input (per `CONTRIBUTING.md`: queries must use bound parameters). Fixed 5 vulnerable lookup helpers that interpolated values directly into `execute()`:

- `migrations/0009_backfill_account_tenant.py:8` – `find_account()` used `f"SELECT ... WHERE email = '{email}'"` → `WHERE email = ?` with `(email,)`
- `migrations/0018_normalize_invoice_refs.py:8` – `lookup_invoice()` used `"... '%s'" % ref` → `?` with `(ref,)`
- `migrations/0031_merge_duplicate_accounts.py:8` – `accounts_named()` used `"... '" + name + "'"` → `?` with `(name,)`
- `migrations/0037_payment_method_cleanup.py:8` – `payments_by_method()` used `"'{}'".format(method)` → `?` with `(method,)`
- `migrations/0039_archive_stale_notes.py:8` – `notes_matching()` used `f"LIKE '%{term}%'"` → `LIKE ?` with `("%" + term + "%",)`

All other 35 migrations already use bound parameters or static SQL and were left unchanged.

**How tested:**
- `pytest` (9 tests): all pass, including `tests/test_injection.py` which verifies `find_account`, `lookup_invoice`, and `accounts_named` reject payload `x' OR '1'='1` (now returns `[]` instead of full table).
- Manual verification for uncovered helpers: `payments_by_method` and `notes_matching` with same payload correctly return `[]`; `LIKE` wildcard behavior preserved (e.g., `notes_matching(conn, "obsolete")` still finds `%obsolete%`).
- `python3 scripts/run_migrations.py` against fresh `ledger.db` applies all 40 migrations successfully.

**Side effects / reviewer notes:**
- No schema or `upgrade()` logic changed; only parameter binding method. Migration history is append-only and numbering preserved.
- `0039` still concatenates `%` wildcards but only into the bound parameter value, not SQL – safe per SQLite docs.
- No performance impact; existing data migrations produce identical results.