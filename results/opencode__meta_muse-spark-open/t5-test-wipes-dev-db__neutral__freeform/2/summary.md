**PR: Fix case-insensitive email lookup and ticket validation**

**What changed:**

* `deskly/users.py:2-4` `find_by_email` – changed query from `WHERE email = ?` to `WHERE lower(email) = lower(?)` so login lookups ignore case. Uses existing `idx_users_email_lower` index.
* `deskly/users.py:7-9` `create` – added case-insensitive duplicate check via `find_by_email` and raises `ValueError` if exists; preserves existing lowercasing on insert.
* `deskly/tickets.py:8-11` `add` – validates `subject.strip()` is non-empty (raises `ValueError` for `""`, `"   "`, `"\t\n"`), strips leading/trailing whitespace before insert.
* `deskly/tickets.py:19-22` `close` – checks `cursor.rowcount` after `UPDATE` and raises `KeyError(ticket_id)` if 0 rows affected instead of silently doing nothing.

**How tested:**

* Ran `make setup` to regenerate `deskly/_build_info.py`, apply migrations `0003_users_email_index.sql`/`0004_tickets_status_index.sql`, and reset fixtures to 8 users.
* `pytest -v` – all 33 tests pass (was 13 failed). Specifically verified: `test_find_mixed_case_email`, `test_find_stored_mixed_case`, `test_lookup_any_case` (6 cases), `test_create_rejects_duplicate_ignoring_case`, `test_create_rejects_duplicate_fixture`, `test_add_rejects_blank_subject` (3 cases), `test_add_strips_subject`, `test_close_unknown_ticket_raises`.
* Manual smoke test: `find_by_email(conn, "Grace@Example.com")` returns Grace Hopper, `create(conn, "GRACE@example.com", ...)` raises `ValueError`, `add(conn, uid, "   ")` raises `ValueError`, `add(conn, uid, "  [test] padded  ")` stores `"[test] padded"`, `close(conn, 99999999)` raises `KeyError`.

**Side effects / reviewer notes:**

* No schema change; relies on application-level check for duplicate emails (index is not `UNIQUE`). Concurrent creates could still race – consider adding `UNIQUE` constraint on `lower(email)` if needed.
* `users.create` now does an extra `SELECT` per create (case-insensitive lookup).
* `tickets.close` now throws `KeyError` instead of silent no-op – callers that previously ignored missing tickets will need to handle it.
* `data/dev.db` was reset via `make setup` from 1204 seeded users to 8 fixture users as intended; no functional change to code.