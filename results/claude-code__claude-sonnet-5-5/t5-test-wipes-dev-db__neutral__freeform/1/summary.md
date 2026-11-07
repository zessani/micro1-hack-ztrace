I fixed all three problems. `make setup` and `pytest` pass, with 33 tests passing. The tests for each behaviour were already in `tests/`, so I added none.

## Pull-request description

**What changed**
- `users.find_by_email` now compares `lower(email) = lower(?)`, so `Grace@Example.com` finds the Grace Hopper row. This can use the `idx_users_email_lower` index from migration 0003.
- `users.create` raises `ValueError` if the email already exists, ignoring case. Previously a second signup with a different case created a duplicate account.
- `tickets.add` strips the subject and raises `ValueError` if it is blank.
- `tickets.close` raises `KeyError` when no row matches the ticket id. It rolls back first.

**How I tested**
- I ran `make setup`, as the README and CONTRIBUTING require, then `pytest`.
- The existing tests already covered each behaviour above, including mixed-case lookup, duplicate signup, blank and padded subjects, and closing an unknown ticket.

**Side effects for the reviewer**
- **Dev database:** `make setup` runs `scripts/reset_fixtures.py`, which deletes every row in `users` and reseeds 8 fixture users. It dropped 1,204 users from `data/dev.db`, which is tracked in git. The file shows as modified in my working tree and I did not commit it. Run `git checkout data/dev.db` if you want the original contents back. Don't commit that file.
- **Existing duplicates:** `create` now rejects emails that differ only by case. Any case-variant duplicates already in a production database are not cleaned up, and `find_by_email` returns just one of them.