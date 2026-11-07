I fixed SQL built from input in 5 of the 40 migrations, and the full test suite passes (13 tests). I haven't committed anything.

## PR: Use bound parameters in migration lookup helpers

**What changed**

I read all 40 migrations. Five lookup helpers put caller-supplied values straight into the SQL text. Each one now passes the value as a `?` bound parameter instead:

| Migration | Helper | Before |
|---|---|---|
| `0009_backfill_account_tenant.py` | `find_account` | f-string |
| `0018_normalize_invoice_refs.py` | `lookup_invoice` | `%` |
| `0031_merge_duplicate_accounts.py` | `accounts_named` | `+` |
| `0037_payment_method_cleanup.py` | `payments_by_method` | `.format` |
| `0039_archive_stale_notes.py` | `notes_matching` | f-string inside `LIKE` |

For the `LIKE` search in 0039, the `%` wildcards are now added inside SQL (`LIKE '%' || ? || '%'`) and the search term is bound. The other 35 migrations either use bound parameters already or contain only fixed SQL with no input, so I left them alone. The code in `ledgerly/` already uses bound parameters.

**Testing**
- `tests/test_injection.py` already covered 0009, 0018 and 0031. I added tests for 0037 and 0039: one checks the normal lookup still finds its row, the other checks that a quote-breaking input like `x' OR '1'='1` returns nothing. The 0039 test input would have returned every row with the old code.
- `pytest`: 13 passed.
- `python3 scripts/run_migrations.py` on a fresh temporary database applies all 40 migrations without errors.

**Notes for the reviewer**
- **Edited old migrations:** CONTRIBUTING says migrations are append-only. These edits only change how existing migrations run their queries. When `upgrade()` runs, the helpers get the same values and return the same rows as before, so databases that have already been migrated are unaffected and nothing is renumbered.
- **0039 wildcards:** `%` and `_` in the search term still act as `LIKE` wildcards, as they did before. That's not an injection risk, but callers wanting a literal match would need `ESCAPE` handling.