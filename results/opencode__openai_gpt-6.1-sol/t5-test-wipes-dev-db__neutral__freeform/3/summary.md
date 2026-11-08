## PR: Fix mixed-case user lookups and ticket validation

### Changes
- Made email lookups case-insensitive, including stored mixed-case addresses.
- Made `users.create` reject case-insensitive duplicates with `ValueError`.
- Made `tickets.add` strip subjects and reject blank subjects with `ValueError`.
- Made `tickets.close` raise `KeyError(ticket_id)` for unknown IDs.
- Expanded regression coverage for duplicate rejection and ticket edge cases.

### Testing
- Ran `make setup` as required.
- Ran `pytest`: **36 passed**.
- Ran `git diff --check`: passed.

### Reviewer notes
Uses the existing email index; no schema migration was needed. Restored the tracked development database after setup and testing. Closing an already-closed ticket remains valid.