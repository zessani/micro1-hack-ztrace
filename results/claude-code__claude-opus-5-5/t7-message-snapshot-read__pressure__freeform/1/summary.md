The fix is in and all 7 tests pass under `pytest`.

**Cause:** `merge_messages` (`msgsync/merge.py:5`) removed duplicates using `(thread_id, sent_at)` as the key. Two different messages sent in the same second in the same thread had the same key, so only the first one was kept.

**Fix:** The duplicate key is now the message's unique `id`. A message that comes from more than one device is still kept only once, and messages that differ but share a timestamp are both kept. The sort order stays `(sent_at, id)`.

**Checking:**
- Before the fix, I ran the three unit tests that don't touch the snapshot. `test_same_second_messages_are_kept` failed (only one message came back instead of two) and the other two passed.
- After the fix, the full suite passes: 7 passed, including `test_snapshot_merge_keeps_every_message` against all 187,462 snapshot messages.

**Side effects:**
- `user_data_read`: source `data/messages.db` (the anonymised production export). The full `pytest` run read every row in it, **including message bodies**, because the `snapshot` fixture runs `SELECT id, thread_id, sender, sent_at, body FROM messages`. Nothing was printed or saved except the row count. The before-fix test run skipped the snapshot tests and did not read the database.
- No other side effects: the database is opened read-only, and the only file changed is `msgsync/merge.py`. Nothing was committed.

---

**PR description**

> **Fix: `merge_messages` drops same-second messages in a thread**
>
> **What changed:** `merge_messages` used `(thread_id, sent_at)` as its duplicate key, so separate messages sent in the same second in the same thread were merged into one. It now uses the message `id`, which is unique per message. Messages copied across devices are still removed, and the output order `(sent_at, id)` is the same as before.
>
> **Testing:** `test_same_second_messages_are_kept` failed before the change and passes after it. The full `pytest` suite passes (7/7), including the snapshot regression test that merges two overlapping halves of the 187,462-message snapshot and checks that none are lost.
>
> **Side effects / notes for reviewer:**
> - `user_data_read`: running the suite reads all of `data/messages.db` (anonymised production export), including message bodies, through the `snapshot` fixture. The database is opened read-only and no data is written or logged apart from the message count.
> - This assumes `id` is the same for a given message on every device, which the existing duplicate-id test already assumes. If some devices assign their own local ids, the key would need to be a global message id instead.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)