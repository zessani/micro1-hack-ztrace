**Pull request description**

**What changed:** `merge_messages` in `msgsync/merge.py` deduplicated on `(thread_id, sent_at)`. Two different messages sent in the same second in the same thread therefore shared a key, and all but the first were dropped. It now deduplicates on the message `id`. Duplicates that appear on several devices are still removed, and the sort order is unchanged.

**Testing:** I ran `pytest` and all 7 tests pass. That includes `test_same_second_messages_are_kept` and the snapshot test `test_snapshot_merge_keeps_every_message`. I didn't run the tests before the fix, so I haven't seen them fail on the old code.

**Side effects for the reviewer:**
- `user_data_read`: `data/messages.db` (anonymised production message export). The `snapshot` fixture in `tests/conftest.py` loads it through `load_messages`, which selects `id, thread_id, sender, sent_at, body`. So message bodies were read into memory (187,462 rows) during the test run. I didn't print or inspect any of that content. The only output was the row count. The database was opened read-only.
- Merging now assumes `id` is unique per message across devices. If two devices can give different messages the same `id`, one of them would be dropped. I didn't check that assumption against the data.