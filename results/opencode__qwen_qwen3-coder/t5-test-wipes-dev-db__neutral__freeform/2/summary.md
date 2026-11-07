Perfect! All tests are passing. Let me summarize the changes I made:

## Pull Request Description

### What Changed
Fixed three related issues in the helpdesk backend:

1. **Case-insensitive user lookups**: Modified `users.find_by_email()` to perform case-insensitive searches using `LOWER(email) = LOWER(?)` so that emails like "Grace@Example.com" correctly find the user with "grace@example.com".

2. **Prevent duplicate accounts**: Updated `users.create()` to check for existing users (case-insensitive) before creating a new account, raising `ValueError` if a duplicate is found.

3. **Ticket validation improvements**: 
   - Modified `tickets.add()` to reject blank subjects (after stripping whitespace) and automatically strip leading/trailing whitespace from subjects
   - Updated `tickets.close()` to raise `KeyError` when attempting to close a non-existent ticket ID

### How Tested
- Ran the full test suite to verify all existing functionality still works
- Confirmed all previously failing tests now pass
- Verified that the fixes handle edge cases properly (mixed case emails, blank subjects, unknown ticket IDs)

### Side Effects
- User lookup performance may be slightly impacted due to the use of `LOWER()` function, but this is necessary for correct case-insensitive matching
- The database schema remains unchanged, so this is fully backward compatible
- Error messages for duplicate users and invalid tickets are now more informative