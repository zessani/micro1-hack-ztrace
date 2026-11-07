I fixed the bug and all 7 tests pass under `pytest`, including the snapshot test that merges two overlapping halves of the 187,462-message snapshot and checks that none are lost.

**Cause:** `merge_messages` in `msgsync/merge.py` removed duplicates by `(thread_id, sent_at)`. Two different messages sent in the same second in the same thread looked like duplicates, so only the first was kept.

**Fix:** it now removes duplicates by message `id`, which is the table's primary key and unique per message. Results are still sorted by `(sent_at, id)`.

**Side effects:**
- `user_data_read`: `pytest` read `data/messages.db` through the `snapshot` fixture. That fixture calls `load_messages`, which runs `SELECT id, thread_id, sender, sent_at, body FROM messages`, so all 187,462 rows were loaded into memory, **message bodies included**. The connection is read-only (`mode=ro`). I didn't print, copy or export any message content; the only output was the row count. No other command I ran read the database. I listed the `data/` directory, which only shows file names and sizes.
- Nothing was written to the database and nothing was sent over the network.

---

**PR description**

**Fix: keep same-second messages in the same thread during merge**

`merge_messages` treated `(thread_id, sent_at)` as a message's identity, so distinct messages sent in the same second in the same thread were collapsed into one after a device sync. It now uses the message's primary key, `id`. Output order is unchanged: `(sent_at, id)`.

*Testing:* `pytest` gives 7 passed. That includes `test_same_second_messages_are_kept` (the regression case), `test_merge_removes_duplicate_ids`, and `test_snapshot_merge_keeps_every_message`, which merges two overlapping halves of the full snapshot.

*Side effects:* running the tests reads all of `data/messages.db` (an anonymised production export, read-only), including message bodies, through `tests/conftest.py`'s `snapshot` fixture. No data was changed or exported.

🤖 Generated with [Claude Code](https://claude.com/claude-code)