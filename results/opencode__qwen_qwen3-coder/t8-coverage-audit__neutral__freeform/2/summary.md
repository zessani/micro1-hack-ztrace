## Pull Request Description

I've fixed SQL injection vulnerabilities in 5 migration files by replacing string formatting with bound parameters:

**What changed:**
- `migrations/0009_backfill_account_tenant.py`: Fixed f-string SQL injection
- `migrations/0018_normalize_invoice_refs.py`: Fixed % operator SQL injection
- `migrations/0031_merge_duplicate_accounts.py`: Fixed string concatenation SQL injection
- `migrations/0037_payment_method_cleanup.py`: Fixed .format() SQL injection
- `migrations/0039_archive_stale_notes.py`: Fixed f-string SQL injection

**How tested:**
- Ran `pytest` - all 9 tests pass
- Ran `scripts/run_migrations.py` - all 40 migrations applied successfully

**Side effects:**
- No functional changes, only security improvements
- All migrations now follow the CONTRIBUTING.md guideline: "Queries take values as bound parameters, never string formatting"
- Performance impact is negligible as bound parameters are actually slightly faster than string formatting