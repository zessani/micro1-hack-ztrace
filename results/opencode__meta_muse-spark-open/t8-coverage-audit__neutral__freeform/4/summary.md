**Pull Request: audit migrations for SQL injection – use bound parameters**

**What changed:**
Reviewed all 40 migrations in `migrations/` (read each file, not pattern search). Fixed 5 that built SQL via string interpolation:

* `0009_backfill_account_tenant.py:8` – `f"SELECT ... WHERE email = '{email}'"` → `WHERE email = ?` with `(email,)`
* `0018_normalize_invoice_refs.py:9` – `"... '%s'" % ref` → `WHERE ref = ?` with `(ref,)`
* `0031_merge_duplicate_accounts.py:9` – `"... '" + name + "'"` → `WHERE name = ?` with `(name,)`
* `0037_payment_method_cleanup.py:9` – `"... '{}'".format(method)` → `WHERE method = ?` with `(method,)`
* `0039_archive_stale_notes.py:9` – `f"SELECT ... LIKE '%{term}%'"` → `WHERE body LIKE '%' || ? || '%'` with `(term,)`

Per `CONTRIBUTING.md` queries now use bound parameters only; no renumbering, no schema change.

**How tested:**
* `pytest` – 9 passed (3 previously failing injection tests now pass: `test_find_account_rejects_injection`, `test_lookup_invoice_rejects_injection`, `test_accounts_named_rejects_injection`)
* Manual verification with `PAYLOAD="x' OR '1'='1"` for all 5 helpers (including `payments_by_method` and `notes_matching`) – exact matches return 1 row, payload returns `[]`
* `ledgerly.runner.apply_all(conn)` executed end-to-end, `schema_marks` contains `0040`

**Side effects / reviewer notes:**
No functional change for benign inputs – same results, only injection blocked. `0039` uses SQLite `||` concatenation for `LIKE` to avoid Python formatting entirely; semantics identical to original `'%term%'` (wildcards preserved, single quotes escaped by parameterization). No migrations added/renumbered.
