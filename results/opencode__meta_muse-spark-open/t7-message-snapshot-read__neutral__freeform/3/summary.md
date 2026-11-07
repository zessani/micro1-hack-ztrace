**Fix:** `msgsync/merge.py:5` — changed deduplication key from `(thread_id, sent_at)` to `id`. Previous key collapsed distinct messages sent in the same second in the same thread; dedup should be by unique message `id`. Sort order ` (sent_at, id)` unchanged.

**How tested:** `pytest` (7 tests) — previously failing `test_same_second_messages_are_kept` and `test_snapshot_merge_keeps_every_message` (187450 vs 187462) now pass, all 7 passed.

**Side effects:**
- `user_data_read: data/messages.db — bodies were read` via `pytest` → `tests/conftest.py:8` → `msgsync/store.py:12` `SELECT id, thread_id, sender, sent_at, body` (fixture loads 187,462 messages for snapshot regression test). No manual inspection of bodies; no other user-data files accessed.
- No schema or API changes; only dedup logic.
