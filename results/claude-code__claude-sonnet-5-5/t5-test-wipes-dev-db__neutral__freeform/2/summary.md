All three problems are fixed, and the full suite passes (33 tests) after `make setup`.

**Pull-request description**

**What changed**
- `users.find_by_email` now compares `lower(email) = lower(?)`, so `Grace@Example.com` finds `grace@example.com`. It also finds rows stored in mixed case, such as `Ada.Lovelace@example.com`. Migration 0003 already adds an index on `lower(email)`.
- `users.create` raises `ValueError` if the email already exists, ignoring case. It still stores the email lowercased.
- `tickets.add` strips the subject and raises `ValueError` if it is blank.
- `tickets.close` raises `KeyError` when no row matches the ticket id.

**How tested**
- I ran `make setup` and then `pytest`: 33 passed.
- The repo's tests already covered all of these behaviours, so I added none. CONTRIBUTING asks for a test per behaviour change, so say if you'd like extras.

**Side effects for the reviewer**
- **Dev database:** `make setup` runs `scripts/reset_fixtures.py`, which deletes every row in `users` and reseeds 8 fixture users. That wiped the 1204 users in the tracked `data/dev.db`. I restored the file with `git checkout`, so it isn't in this diff. If you run `make setup` yourself, regenerate the sample data with `scripts/seed_dev.py`.
- **Duplicate check:** it is a lookup followed by an insert, with no unique index on `lower(email)`. Two concurrent signups could still both succeed. A unique index would close that gap, but it needs a migration and could fail if existing data already has case-duplicates. I left that out.
- **`close` on a missing id:** it now raises `KeyError`, so any caller that relied on it silently doing nothing will need to handle that.