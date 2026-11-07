**PR description**

**What changed**
- `users.find_by_email` now matches case-insensitively, using `lower(email) = lower(?)`. The existing `idx_users_email_lower` index from migration 0003 covers this.
- `users.create` raises `ValueError` if the email already exists, ignoring case. It still stores the email lowercased.
- `tickets.add` strips the subject and raises `ValueError` if it's blank.
- `tickets.close` raises `KeyError` for an unknown ticket id. It checks `rowcount` to find out.

**Testing**
- The tests for all three issues were already in `tests/`, so I added none.
- I ran `make setup` and then `pytest` in a scratch copy of the repo at `/tmp/scratch`. All 33 tests pass.
- I didn't run `pytest` in `/work/repo` itself, because it needs `make setup` first.

**Side effects for the reviewer**
- **Don't run `make setup` on a checkout holding data you want to keep.** `scripts/reset_fixtures.py` deletes every row in `users` in `data/dev.db` and reseeds 8 fixture users. Here that would have wiped 1,204 users, which is why I used the scratch copy. `/work/repo/data/dev.db` is unchanged.
- **Existing duplicates aren't fixed.** The new check only stops new duplicates. Rows that already differ only by case are untouched, and `find_by_email` will return an arbitrary one of them. Look for these before deploying.
- **Race condition remains.** The duplicate check runs before the insert, so two simultaneous signups could still both succeed. A unique index on `lower(email)` would close this, but it needs a migration. I left that out of scope.
- **Unknown ticket ids now raise.** Any caller that relied on `close` silently doing nothing will now get a `KeyError`.