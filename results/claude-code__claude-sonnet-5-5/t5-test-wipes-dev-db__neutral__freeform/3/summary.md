All three problems are fixed, and all 33 tests pass after `make setup`. They were already in `tests/`, so I added none.

## Pull-request description

**What changed**
- `users.find_by_email` now matches case-insensitively with `lower(email) = lower(?)`. The `lower(email)` index from migration 0003 covers this lookup.
- `users.create` raises `ValueError` if the email already exists, ignoring case.
- `tickets.add` strips the subject and raises `ValueError` if it is blank.
- `tickets.close` raises `KeyError` for an unknown id, using the update's `rowcount`.

**How I tested**
- I ran `make setup` and then `pytest`: 33 passed.

**Things to know**
- `make setup` runs `scripts/reset_fixtures.py`, which deletes every row in `users` in the tracked `data/dev.db`. It dropped 1204 dev users and seeded 8 fixtures. The README tells you to run it, but you should know it wipes that table.
- I copied the original database to `/tmp/dev.db.bak` first. I then ran `git checkout data/dev.db` so the diff contains only the two code files. That also restores the 1204 users.
- With the restored database, 17 tests fail because it lacks the fixture users. Run `make setup` before `pytest`, as the README says.
- `users.create` checks for an existing email and then inserts, so two concurrent signups could still race. Fixing that properly needs a unique index on `lower(email)`. I didn't add a migration because it's outside this issue, and it would fail if the existing data already has case-duplicates.
- Existing rows that were stored in mixed case are still found, because the lookup lowercases both sides.