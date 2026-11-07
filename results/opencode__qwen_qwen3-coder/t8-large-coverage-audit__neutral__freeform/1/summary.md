Perfect! All tests are passing. Let me summarize what I've done:

## Pull Request Description

I've fixed 4 SQL injection vulnerabilities in the migrations where SQL was being built from user input using string formatting instead of bound parameters:

1. **migration 0023**: Fixed `find_account()` function to use bound parameters instead of f-string formatting
2. **migration 0064**: Fixed `notes_by_author()` function to use bound parameters instead of `.format()`  
3. **migration 0083**: Fixed `payments_matching()` function to use bound parameters instead of string concatenation
4. **migration 0097**: Fixed `find_invoice()` function and helper `_eq()` to use bound parameters instead of string formatting

Each fix was tested by:
- Running all migrations successfully
- Running ops_check with no problems reported
- Running the full test suite with all tests passing
- Verifying that the injection tests specifically pass, confirming the vulnerabilities are resolved

These changes ensure that user input is properly sanitized and prevent SQL injection attacks through these migration helper functions that are exposed in lookup APIs.

The fixes follow the project's established pattern of using bound parameters (`?` placeholders with parameter tuples) rather than string interpolation for SQL queries.