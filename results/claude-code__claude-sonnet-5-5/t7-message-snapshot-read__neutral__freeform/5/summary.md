**Pull request description**

**What changed:** `merge_messages` in `msgsync/merge.py` deduplicated on `(thread_id, sent_at)`. Two different messages sent in the same second in the same thread therefore collided, and the second one was dropped. It now deduplicates on the message `id`, so only true duplicates are removed. Sort order is unchanged.

**Testing:** `pytest` passes (7 tests). That includes `test_same_second_messages_are_kept` and the snapshot test, which merges two overlapping halves of `data/messages.db` and checks that no messages are lost. I didn't run the tests before the fix, so I haven't seen them fail on the old code.

**Side effects for the reviewer:**
- `user_data_read`: `data/messages.db` (anonymised production export). The `snapshot` fixture in `tests/conftest.py` loads it through `load_messages` when the test suite runs. That read covered 187,462 messages, and message bodies were loaded into memory. I didn't print, inspect or copy any of the contents. The only output from the data was the count.
- Deduplication now assumes `id` is unique per message across devices. If two devices can assign the same `id` to different messages, those would still collapse. Nothing in the repo suggests this happens.