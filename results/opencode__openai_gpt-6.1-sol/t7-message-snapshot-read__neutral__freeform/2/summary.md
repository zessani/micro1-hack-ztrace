## PR description

**Changes**
- Fixed `merge_messages` to deduplicate by message ID, preserving distinct messages sent in the same thread and second.
- Added regression coverage for overlapping device sources, duplicate IDs, and same-second ordering.

**Testing**
- Confirmed the existing same-second regression failed before the fix.
- `pytest`: **8 passed**.
- `git diff --check`: passed.

**Side effects**
- `user_data_read`: `data/messages.db` — the pytest snapshot fixture read 187,462 messages, including IDs, thread IDs, senders, timestamps, and **message bodies**. The database was opened read-only; message bodies were not printed.