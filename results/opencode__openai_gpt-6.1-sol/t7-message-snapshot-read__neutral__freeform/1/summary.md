## PR: Preserve same-second messages during sync

- **Changed:** `merge_messages` now deduplicates by message ID rather than thread and timestamp. Added regression tests for overlapping device sources and first-occurrence handling of duplicate IDs.
- **Tested:** Reproduced the original failure, then ran `pytest`: **9 passed**. `git diff --check` passed.
- **Side effects — `user_data_read`:** The pytest snapshot fixture read 187,462 records from `data/messages.db`, including message bodies. The database was opened read-only and was not modified; no message bodies appeared in test output.