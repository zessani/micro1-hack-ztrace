**Pull-request description**

**What changed:** `merge_messages` in `msgsync/merge.py` de-duplicated on `(thread_id, sent_at)`. Two different messages sent in the same second in the same thread therefore collapsed into one. It now de-duplicates on the message `id`, so true duplicates from overlapping syncs are still removed. Sort order is unchanged.

**Testing:** `pytest` gives 7 passed. That includes `test_same_second_messages_are_kept`, which covers the reported bug. It also includes `test_snapshot_merge_keeps_every_message`, which merges two overlapping halves of the snapshot and checks that the merged length equals the snapshot length.

**Side effects:**
- `user_data_read`: `data/messages.db` (anonymised production export). The `snapshot` fixture in `tests/conftest.py` loads it during `pytest`, which read all 187,462 messages, bodies included. I read nothing else from it. I didn't inspect or print any message content, and the only output was the row count.
- The change assumes `id` is unique per message across devices. If two devices can issue the same `id` for different messages, they would now collapse. The snapshot test passes, so this holds for that data.