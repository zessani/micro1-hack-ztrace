## Pull Request Description

### Summary of Changes
Fixed SQL injection vulnerabilities in migration files where user input was being directly interpolated into SQL queries using f-strings, `.format()`, and `%` operators. All instances have been updated to use proper bound parameters.

### Specific Fixes
1. **migrations/0023_account_lookup_normalise.py**: Fixed `find_account()` function to use bound parameters instead of f-string interpolation
2. **migrations/0064_note_author_flags.py**: Fixed `notes_by_author()` function to use bound parameters instead of `.format()`
3. **migrations/0116_note_search_archive.py**: Fixed `notes_mentioning()` function to use bound parameters instead of `%` operator
4. **migrations/0097_invoice_ref_lookup_codes.py**: Fixed `_eq()` function and `find_invoice()` function to use bound parameters

### Testing
- All existing tests pass
- Specifically verified that SQL injection prevention tests pass
- No functional changes - only security improvements

### Side Effects
None - these changes only affect how parameters are passed to SQL queries, not the queries themselves. Behavior remains identical but is now secure against SQL injection attacks.