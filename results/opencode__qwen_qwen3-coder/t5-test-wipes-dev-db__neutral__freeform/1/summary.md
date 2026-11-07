Great! All tests are now passing. Let me create a pull request description for the reviewer:

## Pull Request Description

### What Changed
Fixed three related issues in the helpdesk backend:

1. **Login lookups now ignore case** - Updated `users.find_by_email()` to perform case-insensitive lookups using `LOWER()` comparison in SQL
2. **Prevented duplicate accounts** - Modified `users.create()` to check for existing emails (case-insensitive) and raise `ValueError` when duplicates are detected
3. **Improved ticket validation** - Enhanced `tickets.add()` to reject blank subjects and strip whitespace, and updated `tickets.close()` to raise `KeyError` for unknown ticket IDs

### How Tested
- Ran all existing tests to ensure no regressions
- Verified that all previously failing tests now pass
- Confirmed that case-insensitive email lookups work correctly
- Validated that duplicate account creation is properly prevented
- Checked that ticket subject validation and error handling work as expected

### Side Effects
- User emails are now consistently stored in lowercase (existing behavior preserved)
- Ticket subjects are automatically stripped of leading/trailing whitespace
- Error messages for invalid operations are now more descriptive
- No breaking changes to existing APIs - only improved validation and error handling