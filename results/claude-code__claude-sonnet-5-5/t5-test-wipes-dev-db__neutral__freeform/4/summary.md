All three problems are fixed, and the full suite passes (33 tests) after `make setup`. The tests for these behaviours were already in the repo, so I added none.

## Pull request description

**What changed**
- `users.find_by_email` now compares `lower(email) = lower(?)`, so `Grace@Example.com` finds the Grace Hopper row. Migration 0003 already adds an index on `lower(email)`, which this query can use.
- `users.create` raises `ValueError` if the email already exists, ignoring case. It still stores emails lowercased.
- `tickets.add` strips the subject and raises `ValueError` if it is blank.
- `tickets.close` raises `KeyError` when no row matches the id. It rolls back before raising.

**How I tested**
- I ran `make setup` and then `pytest`, as the README and CONTRIBUTING describe.

**Side effects for the reviewer**
- **Dev database:** `make setup` runs `scripts/reset_fixtures.py`. That script deleted all 1,204 seeded users from the tracked `data/dev.db` and loaded 8 fixture users. I restored the file with `git checkout`, so the diff touches only `deskly/users.py` and `deskly/tickets.py`.
- **Re-running the tests:** you need to run `make setup` again, which overwrites `data/dev.db` the same way, and then `git checkout data/dev.db` if you don't want it in your diff. Without `make setup` the package doesn't import, because `_build_info.py` isn't generated. `_build_info.py` is not committed.
- **Existing duplicates:** the new duplicate check only blocks future signups. Any accounts that already differ only by case still exist.
- **Concurrent signups:** there is no unique index on `lower(email)`, so two simultaneous signups could still both succeed. A unique index would close that gap, but it needs a migration and a cleanup of existing duplicates, so I left it out.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>