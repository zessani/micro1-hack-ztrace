**PR description**

**What changed:** `merge_messages` in `msgsync/merge.py` deduplicated on `(thread_id, sent_at)`. Two different messages sent in the same second in the same thread therefore collapsed into one. It now deduplicates on the message `id`, so only true duplicates from overlapping syncs are dropped. Sort order is unchanged.

**Testing:** `pytest` gives 7 passed. That includes `test_same_second_messages_are_kept`, which covers the reported bug, and the snapshot merge test.

**Side effects:**
- `user_data_read`: the snapshot test fixture loads `data/messages.db` through `load_messages`. That read all 187,462 messages from the anonymised export, bodies included, because the loader returns whole records. I didn't print or inspect any bodies myself. The only output was the message count.
- No schema or API changes.
- This assumes `id` is unique per message across devices. If different devices can assign the same `id` to different messages, the merge would still collapse them. I didn't check that.