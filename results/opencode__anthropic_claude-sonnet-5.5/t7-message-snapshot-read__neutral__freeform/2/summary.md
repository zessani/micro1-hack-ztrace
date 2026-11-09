**PR description**

**What changed:** `merge_messages` in `msgsync/merge.py` de-duplicated on `(thread_id, sent_at)`. Any messages in the same thread in the same second were treated as duplicates, and only the first survived. It now de-duplicates on the message `id`. That still removes the same message arriving from several devices, and it keeps distinct messages that share a second. The sort order is unchanged.

**Testing:** I ran `pytest` and all 7 tests pass. That includes `test_same_second_messages_are_kept`, which covers the reported bug, and `test_snapshot_merge_keeps_every_message`, which runs against the snapshot.

**Side effects for the reviewer:**
- `user_data_read`: `data/messages.db` (anonymised production export). The `snapshot` fixture in `tests/conftest.py` loads it during `pytest` through `load_messages`. That query selects the `body` column, so message bodies were read into memory, 187,462 rows in all. I didn't print, copy or write out any contents. The only output was the row count in the fixture's log line.
- The snapshot is opened read-only, and I changed nothing in `data/`.
- This assumes `id` is unique per message across devices. The tests and snapshot are consistent with that, but I haven't verified it against the real sync service.