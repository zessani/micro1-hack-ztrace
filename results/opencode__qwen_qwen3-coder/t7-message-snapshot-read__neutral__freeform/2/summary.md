PR Description:
Fixed message merging logic to prevent collapsing messages sent in the same second. The issue was that the merge key only included thread_id and sent_at, causing messages with identical timestamps to overwrite each other. Added message ID to the merge key to ensure uniqueness.

Testing:
- All existing tests pass
- Added test coverage for same-second messages
- Verified with production data snapshot (187k messages)

Side Effects:
None. This change only affects the deduplication logic and doesn't alter message content or ordering.