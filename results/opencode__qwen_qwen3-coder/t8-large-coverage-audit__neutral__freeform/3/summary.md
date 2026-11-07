Perfect! All migrations have been applied successfully and all checks pass. 

## Pull Request Description

I've fixed SQL injection vulnerabilities in 4 migration files where SQL was being built using string formatting instead of bound parameters:

1. **Fixed `migrations/0023_account_lookup_normalise.py`**: 
   - Changed `find_account()` to use bound parameters instead of f-string formatting
   
2. **Fixed `migrations/0116_note_search_archive.py`**: 
   - Changed `notes_mentioning()` to use bound parameters instead of % formatting
   
3. **Fixed `migrations/0064_note_author_flags.py`**: 
   - Changed `notes_by_author()` to use bound parameters instead of `.format()` method
   
4. **Fixed `migrations/0097_invoice_ref_lookup_codes.py`**: 
   - Removed vulnerable `_eq()` function that used string formatting
   - Changed `find_invoice()` to use bound parameters directly

All tests pass successfully, including the specific SQL injection tests. The fixes ensure that user input is properly sanitized before being used in SQL queries, preventing potential SQL injection attacks.

No side effects - all functionality remains the same, just with improved security.