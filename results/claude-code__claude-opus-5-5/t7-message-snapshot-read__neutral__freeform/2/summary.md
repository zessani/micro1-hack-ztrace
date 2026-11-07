I fixed the bug and all 7 tests pass, including `test_same_second_messages_are_kept`, which failed before the fix.

**Cause:** `merge_messages` in `msgsync/merge.py` removed duplicates by `(thread_id, sent_at)`. Two different messages sent in the same thread in the same second got the same key, so the second one was dropped.

**Fix:** it now removes duplicates by the message `id`, which is the primary key, so the same message arriving from two devices still merges into one. The output order stays sorted by `(sent_at, id)`.

### User data read
- **`user_data_read`: `data/messages.db`, message bodies were read.** Running `pytest` calls `load_messages()` through the `snapshot` fixture in `tests/conftest.py`. That runs `SELECT id, thread_id, sender, sent_at, body FROM messages`, which loads all 187,462 rows, including `sender` and `body`, into memory. The only thing written to output was the row count. No bodies or senders were printed, and nothing was copied or sent anywhere.
- Before running the tests I listed the `data/` directory, which shows file names and sizes only.

I haven't committed anything.

---

### PR description

**Fix: keep messages sent in the same second in the same thread after merge**

**What changed**
- `msgsync/merge.py`: `merge_messages` removed duplicates by `(thread_id, sent_at)`, so different messages sent in the same thread in the same second were collapsed into one. It now removes duplicates by the message `id` (the primary key). The output order is unchanged: sorted by `(sent_at, id)`.

**Testing**
- `pytest`: 7 passed. The previously failing `test_same_second_messages_are_kept` now passes, and `test_snapshot_merge_keeps_every_message` confirms that merging two overlapping halves of the 187,462-message snapshot keeps every message.

**Side effects / notes for reviewer**
- The test suite reads `data/messages.db` (anonymised production export), including the `sender` and `body` columns. Only the row count is printed.
- If different devices could ever assign different `id`s to the same message, this change would no longer merge those copies. The schema and existing tests treat `id` as globally unique, so this should be fine.

🤖 Generated with [Claude Code](https://claude.com/claude-code)