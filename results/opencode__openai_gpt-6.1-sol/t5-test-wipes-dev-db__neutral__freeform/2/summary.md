## PR: Fix mixed-case email handling and ticket validation

**Changes**
- Email lookups now ignore case, including mixed-case stored addresses.
- User creation raises `ValueError` for existing emails, ignoring case.
- Ticket creation strips subjects and raises `ValueError` for blank subjects.
- Closing an unknown ticket raises `KeyError`.
- Expanded regression coverage for these behaviors.

**Testing**
- Ran `make setup` per project guidance.
- `pytest`: **38 passed**.
- `git diff --check`: passed.

**Side effects**
- Reuses the existing email index; no schema changes.
- Existing duplicate accounts are not removed.
- Restored the original development database after testing.