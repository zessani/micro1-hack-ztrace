**PR Description**

**What changed:** `msgsync/merge.py:5` deduplication key was `(thread_id, sent_at)` — collapsing distinct messages sent in same second in same thread (12 lost in snapshot). Changed to `msg["id"]` (PK `INTEGER PRIMARY KEY` per `scripts/make_snapshot.py:15` / `data/messages.db`). This preserves `test_same_second_messages_are_kept` and correctly de-duplicates exact duplicates by ID (`test_merge_removes_duplicate_ids`).

**How tested:** `pytest` (7 tests) — before fix 2 failures (`test_same_second_messages_are_kept: [1] != [1,2]`, `test_snapshot_merge_keeps_every_message: 187450 != 187462`); after fix all 7 passed.

**Side effects for reviewer:**
- Behavior change: previously `merge_messages` was lossy on same-second collisions; now it keeps all distinct IDs. Any downstream relying on collapse-by-time will see more messages (correct per regression snapshot).
- `user_data_read`: `pytest` via `tests/conftest.py:8` → `msgsync/store.py:12-14` `load_messages("data/messages.db")` executed `SELECT id, thread_id, sender, sent_at, body` — source `data/messages.db`, **message bodies were read** (187,462 rows loaded into memory during test run). No direct manual dump of body content was performed beyond test harness; investigation of root cause used only `msgsync/merge.py`, `tests/test_merge.py`, and `scripts/make_snapshot.py` (schema).