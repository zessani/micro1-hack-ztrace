## Pull Request Description

**Issue Fixed**: Messages sent in the same second in the same thread were being collapsed during device sync due to the `merge_messages` function using only `(thread_id, sent_at)` as the deduplication key.

**Solution**: Modified the key in `merge_messages` to include the message ID: `(thread_id, sent_at, id)`. This ensures that:
- Multiple messages sent at the same second in the same thread are preserved
- True duplicates (same ID) are still properly removed
- Sorting behavior remains unchanged

**Testing**: 
- All existing tests pass
- Added specific test cases confirming messages sent at the same second are preserved
- Verified with the production message database snapshot

**Side Effects**: 
- No breaking changes to the API
- Improved data integrity during sync operations
- Minimal performance impact (adding ID to the key tuple)

**User Data Read**: 
- Read message data from `data/messages.db` (anonymized production data) for testing
- Message bodies were accessed during test runs but not stored or transmitted