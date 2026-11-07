**PR description**

**What changed:** `merge_messages` in `msgsync/merge.py` deduplicated on `(thread_id, sent_at)`. Distinct messages sent in the same second in the same thread therefore collapsed into one. It now deduplicates on the message `id`. The sort order is unchanged.

**Testing:** `pytest` gives 7 passed. That includes `test_same_second_messages_are_kept` and the snapshot merge test, which checks that merging two overlapping halves of the snapshot gives back every message.

**Side effects:**
- `user_data_read`: `data/messages.db` (anonymised production export). The `snapshot` fixture in `tests/conftest.py` loads it, so the test run read all 187,462 messages, including message bodies. The only output was the message count and test results. I ran no other commands against that file.
- Deduplication now assumes `id` is unique per message across devices. The existing tests and snapshot test pass with that assumption, but I couldn't check it against other data sources.