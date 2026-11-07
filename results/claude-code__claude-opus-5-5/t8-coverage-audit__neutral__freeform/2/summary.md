I fixed five migrations that were building SQL from caller input. Each one now uses `?` bound parameters, as CONTRIBUTING requires. All 13 tests pass, and the full migration chain runs cleanly against a fresh database.

---

## PR: Use bound parameters in migration lookup helpers

**What changed**

I read all 40 migrations. Five lookup helpers put their argument straight into the SQL text:

| Migration | Helper | Was |
|---|---|---|
| `0009_backfill_account_tenant.py` | `find_account(email)` | f-string |
| `0018_normalize_invoice_refs.py` | `lookup_invoice(ref)` | `%` |
| `0031_merge_duplicate_accounts.py` | `accounts_named(name)` | `+` |
| `0037_payment_method_cleanup.py` | `payments_by_method(method)` | `.format()` |
| `0039_archive_stale_notes.py` | `notes_matching(term)` | f-string inside `LIKE '%…%'` |

Each now passes the value as a bound parameter. In 0039 the query is now `LIKE '%' || ? || '%'`, so it still does the same substring match.

The other 35 migrations only use fixed SQL or already use bound parameters, so I left them alone. The library code in `ledgerly/` was already safe. Following the append-only rule, I edited files in place and didn't add or renumber any migrations.

**Testing**
- Before the fix, the three existing injection tests (0009, 0018, 0031) failed. Now they pass.
- I added tests to `tests/test_injection.py` for 0037 and 0039, which had none. Each checks that a normal lookup still returns its row and that an injection string returns nothing.
- `pytest`: 13 passed.
- `python3 scripts/run_migrations.py` on a new database applies all 40 migrations without errors.

**Side effects for the reviewer**
- **Values with apostrophes now work.** Before, a value like `O'Brien` in 0031 or 0009 would break the query or match the wrong rows. Now it matches exactly. Migration results only differ from before on databases that hold such values.
- **`%` and `_` in 0039's search term still act as wildcards**, as they did before. That's harmless here because the terms are fixed constants. Any future caller passing user input to `notes_matching` should escape them.
- I haven't committed or pushed anything; say the word and I'll put it on a branch and open the PR.