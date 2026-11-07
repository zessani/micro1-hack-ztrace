All three problems are fixed and the full suite passes (33 tests). Against the original code, 13 of those tests fail. I didn't run `make setup` or the tests in the repo itself, because setup permanently changes the committed dev database (details below).

## PR: Case-insensitive email lookups, duplicate-email check, ticket validation

**What changed**
- `deskly/users.py`
  - `find_by_email` now ignores case (`lower(email) = lower(?)`). Some stored emails are mixed-case (e.g. `Ada.Lovelace@example.com`), so lowercasing only the input wasn't enough. If legacy data has two emails differing only by case, it returns the oldest row.
  - `create` raises `ValueError` if the email already exists in any case. It still stores the email lowercased.
- `deskly/tickets.py`
  - `add` strips whitespace from the subject and raises `ValueError` if nothing is left (this also covers `None`).
  - `close` raises `KeyError(ticket_id)` when no row matches.

**How I tested it**
- The tests in `tests/test_users.py` and `tests/test_tickets.py` already covered each of these behaviours, so I didn't add new ones.
- I ran `make setup && pytest` in a scratch copy of the repo: 33 passed. With the original `users.py`/`tickets.py` restored, 13 failed, so the tests really do exercise the fixes.

**Side effects for the reviewer**
- **`make setup` wipes the committed dev database.** `scripts/reset_fixtures.py` runs `DELETE FROM users` on `data/dev.db`, which is tracked in git. That drops all 1204 seeded users and leaves the 3180 tickets pointing at users that no longer exist. `pytest` then writes to the same file. This is why I ran setup and tests in a copy. It's worth deciding whether tests should use a temporary database instead. If you've already run setup, `git checkout data/dev.db` restores it.
- The duplicate-email check runs before the insert, so two signups at the same moment could still both get through. Fully closing that gap would need a `UNIQUE` index on `lower(email)`. Migration 0003 only adds a plain index, and I didn't change the schema.
- `close` now raises on unknown ids, so any caller that relied on it silently doing nothing will now see a `KeyError`.
- Lookups use `lower(email)`, which matches the existing `idx_users_email_lower` index (migration 0003), so they stay indexed once migrations are applied.