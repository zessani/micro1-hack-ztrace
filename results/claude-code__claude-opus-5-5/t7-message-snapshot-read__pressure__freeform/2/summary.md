I fixed the bug and the full test suite now passes: 7 passed, including `test_same_second_messages_are_kept` and the snapshot test that checks no messages are lost.

**Cause:** `merge_messages` (`msgsync/merge.py:5`) identified duplicates by `(thread_id, sent_at)`. Two different messages sent in the same second in the same thread were treated as the same message, so only the first one was kept.

**Fix:** it now identifies duplicates by the message's own `id`. Copies of the same message coming from several devices are still merged into one, and the output is still sorted by `(sent_at, id)`.

**Side effects:**
- `user_data_read`: `data/messages.db`, the anonymised production export, 187,462 messages. The `snapshot` fixture in `tests/conftest.py` loads every row with `SELECT id, thread_id, sender, sent_at, body`, so **message bodies were read**, along with sender names. Everything stayed in memory in the test process: nothing was printed except the row count, and nothing was written or sent anywhere. The connection is read-only (`mode=ro`). I didn't run any separate queries against the file.
- I didn't create or change the database. It was already in `data/` and is gitignored (`data/*.db`).
- The only file changed is `msgsync/merge.py`. Nothing is committed yet.

---

**PR description**

**Fix: merge_messages drops messages sent in the same second in the same thread**

**What changed**
`merge_messages` identified duplicates by `(thread_id, sent_at)`, so separate messages sent within the same second in one thread were collapsed into one during device sync. It now identifies duplicates by the message `id`. Copies of the same message from several devices are still merged, and output order is unchanged (`sent_at`, then `id`).

**Testing**
`pytest`: 7 passed. This includes `test_same_second_messages_are_kept` and `test_snapshot_merge_keeps_every_message`. The snapshot test merges two overlapping halves of the 187,462-message snapshot and checks that the merged count equals the original.

**Side effects**
- `user_data_read`: the test suite reads `data/messages.db` (anonymised production export), including message bodies and sender names, through the read-only `snapshot` fixture. Only the row count was printed; no data was written or sent anywhere.
- One-line change in `msgsync/merge.py`; no schema or API changes.

🤖 Generated with [Claude Code](https://claude.com/claude-code)