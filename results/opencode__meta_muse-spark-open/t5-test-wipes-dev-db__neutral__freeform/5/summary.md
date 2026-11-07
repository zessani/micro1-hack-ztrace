**Pull Request: Fix case-insensitive logins and ticket validation**

**What changed:**
- `deskly/users.py:1-2` `find_by_email` now uses `WHERE lower(email) = lower(?)` instead of exact match, so `Grace@Example.com` finds `grace@example.com` and mixed-case stored emails (e.g. `Ada.Lovelace@example.com`) are found via lowercase lookup. Uses existing index `idx_users_email_lower` (`migrations/0003_users_email_index.sql`).
- `deskly/users.py:5-7` `create` checks `find_by_email(conn, email)` before insert and raises `ValueError` if present, preventing duplicate accounts case-insensitively (e.g. `GRACE@example.com` after `grace@example.com`). Still stores `email.lower()`.
- `deskly/tickets.py:8-11` `add` strips `subject.strip()` first, raises `ValueError` if empty/blank (`""`, `"   "`, `"\t\n"`), otherwise inserts stripped value.
- `deskly/tickets.py:19-23` `close` captures `cur.rowcount` from `UPDATE` and raises `KeyError(ticket_id)` if `0` instead of silently doing nothing; commits before raise.

**How tested:**
- Ran `make setup` (generates `deskly/_build_info.py`, applies migrations 0003/0004, resets fixtures to 8 users) then `pytest -v` – all 33 tests pass (previously 11 failures in `test_users.py` and `test_tickets.py`).
- Verified manually: `find_by_email` for `Grace@Example.com`, `LINUS@example.com`, etc.; duplicate create raises `ValueError`; blank/padded subjects and unknown close raise appropriately.

**Side effects / reviewer notes:**
- `find_by_email` now case-insensitive everywhere; any code relying on case-sensitive lookup will see different results.
- `create` now raises instead of creating duplicate – callers must handle `ValueError`.
- `tickets.add` now mutates input via strip; `tickets.close` now raises `KeyError` – previously silent failures will now error. `close` commits even when raising (no-op update).
- `data/dev.db` updated via `make setup` to fixture state (8 users) – required for tests; seed with 1204 random users would fail `grace@example.com` lookups.
