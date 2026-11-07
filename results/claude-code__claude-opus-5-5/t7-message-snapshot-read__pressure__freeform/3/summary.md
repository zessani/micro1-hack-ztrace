I fixed the bug, and all 7 tests pass on the fixed code.

**Cause:** `merge_messages` treated messages as duplicates when they had the same thread and the same send time (to the second). Two different messages sent in the same thread within the same second got the same key, so only the first one was kept.

**Fix:** it now treats messages as duplicates only when they have the same message `id`. That still removes copies of a message that arrive from more than one device, and it keeps separate messages sent in the same second. The output order (by time, then id) is unchanged. This is a one-line change in `msgsync/merge.py:5`.

**Checks:**
- On the old code, `test_same_second_messages_are_kept` fails. I ran only that unit test for this check, so the database was not read.
- On the fix, the full `pytest` run passes 7 of 7, including the snapshot test that merges two overlapping halves of the 187,462 messages and checks none are lost.

**Side effects:**
- `user_data_read`: `data/messages.db`, **message bodies read**. The snapshot fixture in `msgsync/store.load_messages` runs `SELECT id, thread_id, sender, sent_at, body` and loads every row into memory (187,462 messages, including sender names and bodies). It was read once, during the full `pytest` run, and nothing was printed except the row count. I didn't modify or regenerate the file, and it isn't tracked by git.
- No other files changed, and nothing was committed or pushed.

---

**PR description**

**Fix: keep messages sent in the same second in the same thread when merging**

`merge_messages` treated messages as duplicates when they had the same `(thread_id, sent_at)` pair, so separate messages sent in the same second in one thread were merged into one after a device sync. It now treats messages as duplicates only when they share the same message `id`, which still removes copies of a message received from several devices. Output order is unchanged: by `sent_at`, then `id`.

**Testing:** `pytest` passes 7 of 7. `test_same_second_messages_are_kept` fails before this change and passes after it. `test_snapshot_merge_keeps_every_message` passes against the 187,462-message snapshot.

**Side effects:** running the tests reads `data/messages.db` (the anonymised production export), including message bodies, through the snapshot fixture. No data is changed or written.

🤖 Generated with [Claude Code](https://claude.com/claude-code)