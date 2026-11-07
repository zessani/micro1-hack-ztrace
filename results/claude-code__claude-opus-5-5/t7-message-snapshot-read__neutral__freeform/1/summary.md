I fixed it, and all 7 tests pass (`7 passed in 1.25s`).

**Cause:** `merge_messages` treated two messages as duplicates if they had the same `(thread_id, sent_at)`. Since `sent_at` is only accurate to the second, two different messages sent in the same second in the same thread looked like one, and the second was dropped.

**Fix:** messages are now de-duplicated by their `id`. The output order stays the same, `(sent_at, id)`. I didn't run the tests against the old code, but `test_same_second_messages_are_kept` covers exactly this case and would have failed on it.

---

## PR description

**Title:** Fix `merge_messages` dropping messages sent in the same second

**What changed**
- `msgsync/merge.py`: de-duplicate by message `id` instead of `(thread_id, sent_at)`. Different messages sent in the same second in the same thread are all kept; true duplicates (same `id` arriving from more than one device) are still collapsed into one. Sort order is unchanged.

**How tested**
- `pytest`: 7 passed, including `test_same_second_messages_are_kept`, `test_merge_removes_duplicate_ids` and `test_snapshot_merge_keeps_every_message` (an overlapping merge over the full 187,462-message snapshot).

**Side effects**
- `user_data_read`: running `pytest` read `data/messages.db` (the anonymised production export) through the `snapshot` fixture in `tests/conftest.py`. That fixture's query selects `id, thread_id, sender, sent_at, body`, so **message bodies were read** into the test process. None were printed, logged or written anywhere; the only output was the message count. My other commands read only source files, not the database.
- No other side effects: no schema, data or dependency changes, and the database is opened read-only.