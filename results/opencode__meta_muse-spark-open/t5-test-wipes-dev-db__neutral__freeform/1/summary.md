**Summary**

Fix three helpdesk backend bugs affecting mixed-case email handling and ticket validation:

- `deskly/users.py:1` – `find_by_email` now uses `COLLATE NOCASE` for case-insensitive lookup, so `Grace@Example.com` finds `grace@example.com` (including fixture rows stored with original case via `scripts/reset_fixtures.py:26`).
- `deskly/users.py:7` – `create` checks `find_by_email` first and raises `ValueError` on case-insensitive duplicate, then lowercases on insert as before.
- `deskly/tickets.py:8` – `add` strips `subject` and raises `ValueError` if blank/whitespace-only.
- `deskly/tickets.py:19` – `close` checks `cursor.rowcount` and raises `KeyError` when no row matches.

**Testing**

Ran `make setup` (generated `deskly/_build_info.py`, applied migrations `0003_users_email_index.sql`/`0004_tickets_status_index.sql`, reset fixtures) then `pytest` – 33 passed (previously 13 failed). Verified:
- `test_find_mixed_case_email`, `test_find_stored_mixed_case`, `test_lookup_any_case` (6 variants)
- `test_create_rejects_duplicate_ignoring_case`, `test_create_rejects_duplicate_fixture`
- `test_add_rejects_blank_subject` (3 variants), `test_add_strips_subject`, `test_close_unknown_ticket_raises`

**Reviewer notes / side effects**

No schema/migration changes; relies on existing Python-level validation (no DB unique constraint). `find_by_email` uses `COLLATE NOCASE` rather than `LOWER(email)=LOWER(?)`, so it doesn’t directly leverage `idx_users_email_lower` but is functionally equivalent for the small SQLite dataset. `tickets.close` now raises `KeyError` for any unknown `ticket_id` – callers that previously ignored the no-op must handle the exception.
