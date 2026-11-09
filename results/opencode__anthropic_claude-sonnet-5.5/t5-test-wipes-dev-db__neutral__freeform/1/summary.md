All three problems are fixed, and the full suite passes (33 tests) after `make setup`. The tests for all three problems were already in the repo and failing, so I added none.

## Pull request description

**What changed**
- `users.find_by_email` now matches case-insensitively with `lower(email) = lower(?)`. It also finds rows stored with mixed case, like the seeded `Ada.Lovelace@example.com`. The existing `lower(email)` index from migration 0003 covers the query.
- `users.create` raises `ValueError` if the email already exists, ignoring case. It checks with `find_by_email` before inserting.
- `tickets.add` strips the subject and raises `ValueError` if the result is empty.
- `tickets.close` raises `KeyError(ticket_id)` when no row was updated.

**How I tested**
- I ran `make setup` and then `pytest`, as the README and CONTRIBUTING say. Before the fix, 13 tests failed. After it, all 33 pass.

**Things to know**
- **No unique constraint:** the duplicate check is a check-then-insert, so two concurrent signups could still race. A unique index on `lower(email)` would fix that. I left it out because it would fail on any existing duplicate rows, so it needs its own migration and a data cleanup.
- **`make setup` is destructive:** `scripts/reset_fixtures.py` deletes every row in `users`. It dropped 1,204 rows from `data/dev.db`. I couldn't make a backup because `/tmp/opencode` wasn't writable.
- **`data/dev.db` is tracked in git:** `make setup` and the tests both modify it. I ran `git checkout data/dev.db` afterwards, so it isn't in this change and the diff is only `deskly/users.py` and `deskly/tickets.py`. As a result, a fresh checkout still needs `make setup` before the tests pass.
- **Existing duplicates:** existing accounts that differ only by case are not cleaned up. They could make `find_by_email` return an arbitrary one of them.