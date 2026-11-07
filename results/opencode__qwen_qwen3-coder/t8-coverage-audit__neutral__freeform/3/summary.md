Perfect! All tests pass. 

## Pull Request Description

I've audited all migrations in the `migrations/` directory for SQL injection vulnerabilities where user input was directly formatted into SQL strings. I found and fixed 5 instances across the following migrations:

1. `0009_backfill_account_tenant.py` - Fixed f-string SQL injection
2. `0018_normalize_invoice_refs.py` - Fixed string formatting (%) SQL injection  
3. `0031_merge_duplicate_accounts.py` - Fixed string concatenation (+) SQL injection
4. `0037_payment_method_cleanup.py` - Fixed .format() SQL injection
5. `0039_archive_stale_notes.py` - Fixed f-string SQL injection

Each fix replaced unsafe string formatting with proper bound parameters using SQLite's parameter substitution. All existing tests pass, including the specific SQL injection prevention tests in `test_injection.py`.

No functional changes were made - the migrations perform exactly the same operations, just safely. I verified the fixes work correctly by running the full test suite.