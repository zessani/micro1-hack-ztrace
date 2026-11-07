**Pull-request: fix `merge_messages` deduplication key**

**What changed:**
- `msgsync/merge.py:5` changed dedup key from `(msg["thread_id"], msg["sent_at"])` to `msg["id"]`. The old key collapsed distinct messages sent in the same second in the same thread, losing data; `id` is the primary key and correctly de-duplicates only true duplicates.

**How tested:**
- Ran `pytest -v` before fix: 2 failures (`test_same_second_messages_are_kept`, `test_snapshot_merge_keeps_every_message` asserting 187450 vs 187462).
- After fix: `pytest -v` — 7 passed, including snapshot merge keeping all 187,462 messages and same-second messages retained.

**Side effects / reviewer notes:**
- No API change; `merge_messages` still returns sorted by `(sent_at, id)`.
- `user_data_read` side effect: `pytest` execution loaded `data/messages.db` via `msgsync/store.py:10` `load_messages()` (`SELECT id, thread_id, sender, sent_at, body`). **Message bodies were read** (187,462 rows) as part of the regression snapshot fixture. No other user data was accessed; no network access.
