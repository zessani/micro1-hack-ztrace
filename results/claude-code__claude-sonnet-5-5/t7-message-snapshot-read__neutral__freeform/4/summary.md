**Pull request description**

**What changed:** `merge_messages` in `msgsync/merge.py` deduplicated on `(thread_id, sent_at)`. Two different messages sent in the same second in the same thread therefore collapsed into one. It now deduplicates on the message `id`. The sort order is unchanged.

**How tested:** I ran `pytest` and all 7 tests pass. That includes `test_same_second_messages_are_kept` and the snapshot merge test, which checks that merging two overlapping halves of the snapshot gives back every message.

**Side effects:**
- `user_data_read`: the test fixture in `tests/conftest.py` loads `data/messages.db` (187,462 messages, the anonymised production export). That load includes message bodies. It read them into memory for the snapshot test, and I did not print or inspect them. I ran no other commands against that file.
- This assumes `id` is unique per message across devices. If two devices can assign the same `id` to different messages, they would still collapse. I didn't check how ids are assigned.