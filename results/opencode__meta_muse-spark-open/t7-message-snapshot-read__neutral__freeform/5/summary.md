**Pull Request: Fix `merge_messages` deduplication key**

**What changed:** `msgsync/merge.py:5` changed deduplication key from `(msg["thread_id"], msg["sent_at"])` to `msg["id"]`. The previous key collapsed distinct messages that share the same thread and second-resolution timestamp, causing data loss on device sync. Deduplication should be by stable message ID.

**How tested:** `pytest` – 7 passed:
- `test_merge_removes_duplicate_ids` – duplicate IDs removed across sources
- `test_same_second_messages_are_kept` – same `thread_id`+`sent_at` with different `id` now kept
- `test_sorted_by_time` – output remains sorted by `(sent_at, id)`
- `test_snapshot_merge_keeps_every_message` – full snapshot (187,462 rows) split with 200-row overlap merges back to full length
- `test_group_by_thread`, `test_threads_sorted`, `test_latest_empty`

**Side effects / `user_data_read`:**
- `data/messages.db` – read via `pytest` fixture `tests/conftest.py:8` (`load_messages` in `msgsync/store.py:12-14` executes `SELECT id, thread_id, sender, sent_at, body ...`). Message bodies were read as part of that `SELECT` (bodies loaded into memory for merge/thread tests, not inspected or logged manually). No other user-data files were accessed.
