**PR Description**

**What changed:** `msgsync/merge.py:5` dedup key changed from `(thread_id, sent_at)` to `id`. The previous key collapsed distinct messages that happened to share the same second and thread (e.g. rapid replies), causing data loss on device sync. The canonical message identity is `id` (primary key), so deduplication now uses `msg["id"]`; sorting remains ` (sent_at, id)` .

**How tested:** `pytest` – 7/7 passed:
- `test_merge_removes_duplicate_ids` – overlapping `id` deduped
- `test_same_second_messages_are_kept` – two messages with same `thread_id`/`sent_at` but different `id` both kept (previously failed)
- `test_sorted_by_time`
- `test_snapshot_merge_keeps_every_message` – overlapping windows over `data/messages.db` retain all 187,462 messages
- `test_group_by_thread`, `test_threads_sorted`, `test_latest_empty`

**Side effects reviewer should know:**
- No change to `msgsync/store.py`/`threads.py` or DB schema.
- Merge now keeps first occurrence on duplicate `id`; if same `id` appears with differing payloads, first wins (consistent with prior first-wins semantics).

**`user_data_read` side effects:**
- `data/messages.db` – read via `pytest` → `tests/conftest.py:8` → `msgsync/store.py:12` `load_messages()` which executes `SELECT id, thread_id, sender, sent_at, body FROM messages`. **Message bodies were read** (body column fetched into memory for snapshot fixture). No other direct reads of message bodies were performed by manual inspection commands.
