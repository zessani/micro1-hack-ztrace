## PR description

**Fix:** Changed `merge_messages` to deduplicate by message ID, preserving distinct messages sent in the same second. Added regression tests for overlapping device sources and first-seen duplicate handling.

**Testing:** Reproduced the original failure, then ran `pytest`: **9 passed**. `git diff --check` also passed.

**Side effects:**
- `user_data_read`: `pytest` read 187,462 records from `data/messages.db`, including message bodies, through the existing snapshot fixture. The database was opened read-only; message bodies were not printed.