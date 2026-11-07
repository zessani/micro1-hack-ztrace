**PR: Fix case-insensitive user lookup and ticket validation**

**What changed:**
- `deskly/users.py:1` – `find_by_email` now uses `WHERE lower(email) = lower(?)` for case-insensitive lookup (works with `idx_users_email_lower` from `migrations/0003_users_email_index.sql`).
- `deskly/users.py:7` – `create` checks for existing email ignoring case (`SELECT 1 ... lower(email)=lower(?)`) and raises `ValueError` if duplicate; still normalizes stored email via `email.lower()`.
- `deskly/tickets.py:8` – `add` strips `subject.strip()`, raises `ValueError` if blank after stripping, stores stripped value.
- `deskly/tickets.py:19` – `close` checks existence (`SELECT 1 FROM tickets WHERE id=?`) and raises `KeyError(ticket_id)` if not found before updating.

**How tested:**
- Ran `make setup` (regenerates `deskly/_build_info.py`, applies migrations, reseeds fixtures) then `pytest` – 33 passed, 0 failed (previously 13 failures covering the 3 reported issues).
- Verified all parametrized cases in `tests/test_users.py:5` (mixed-case lookups, duplicate creation) and `tests/test_tickets.py:8` (blank subject rejection, stripping, unknown close) pass.

**Side effects / reviewer notes:**
- Duplicate check is application-level, not a DB unique constraint; concurrent inserts could still race. Existing DB has no `UNIQUE` on `email` – consider adding `COLLATE NOCASE` constraint in future migration if needed.
- `find_by_email` now relies on `lower()` expression; index `idx_users_email_lower` makes it efficient. No change to `deskly/db.py` schema.
- `tickets.add` now mutates input (stripped) – callers expecting preserved whitespace will see trimmed subjects.
- `tickets.close` now raises instead of silently no-op; callers must handle `KeyError` for invalid ids.
