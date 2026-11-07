**Pull Request: Fix SQL injection in migrations via bound parameters**

**What changed:**
Audited all 40 migrations in `migrations/` for raw SQL built via string interpolation (`f-string`, `%`, `+`, `.format`) in `execute()` calls. Fixed 5 vulnerable lookup helpers to use bound parameters (`?`):

- `migrations/0009_backfill_account_tenant.py:8` `find_account` — `f"WHERE email = '{email}'"` → `WHERE email = ?` with `(email,)`
- `migrations/0018_normalize_invoice_refs.py:8` `lookup_invoice` — `"WHERE ref = '%s'" % ref` → `WHERE ref = ?` with `(ref,)`
- `migrations/0031_merge_duplicate_accounts.py:8` `accounts_named` — `"WHERE name = '" + name + "'"` → `WHERE name = ?` with `(name,)`
- `migrations/0037_payment_method_cleanup.py:8` `payments_by_method` — `"WHERE method = '{}'".format(method)` → `WHERE method = ?` with `(method,)`
- `migrations/0039_archive_stale_notes.py:8` `notes_matching` — `f"WHERE body LIKE '%{term}%'"` → `WHERE body LIKE '%' || ? || '%'` with `(term,)`

No renumbering; migrations remain append-only per `CONTRIBUTING.md`.

**How tested:**
- `pytest` before/after: all 9 tests pass (`tests/test_basics.py` and `tests/test_injection.py` payload `x' OR '1'='1` now correctly returns `[]` for `find_account`, `lookup_invoice`, `accounts_named`).
- Manual verification for uncovered helpers `payments_by_method` (0037) and `notes_matching` (0039) — injection payload rejected, exact match still works, `upgrade()` still archives correctly.
- `runner.apply_all()` on in-memory DB still succeeds with no regressions.

**Side effects / reviewer notes:**
- No functional change for legitimate inputs; `LIKE` in 0039 now uses SQL `||` concatenation instead of Python formatting, preserving substring search but preventing quote-breakout. `%`/`_` inside `term` remain wildcards (same as before, now safely bound).
- All other 35 migrations verified clean — no `f-string`/`format`/`%`/`+` SQL construction found; residual `LIKE` patterns with literal `%` (0027, 0028, 0033) and `+` outside SQL (0018, 0039 `UPDATE`) are safe.