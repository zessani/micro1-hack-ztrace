I fixed all three problems in `deskly/users.py` and `deskly/tickets.py`. All 33 tests pass with the fix; without it, 19 fail. I did **not** run `make setup` in `/work/repo` itself, because it deletes real data from a committed file (details below). I ran it in a throwaway copy instead.

---

## PR: Case-insensitive email lookups, duplicate-account guard, ticket validation

### What changed
- **`users.find_by_email`** now ignores case on both sides: `lower(email) = lower(?)`. Lowering only the input isn't enough, because some stored emails are mixed-case (e.g. `Ada.Lovelace@example.com`). This also lets the query use the existing `idx_users_email_lower` index from migration 0003. If old duplicate rows already exist, `ORDER BY id` makes it return the oldest account every time.
- **`users.create`** raises `ValueError` if an account with that email already exists, ignoring case. New emails are still stored lowercased.
- **`tickets.add`** strips leading/trailing whitespace from the subject and raises `ValueError` if nothing is left.
- **`tickets.close`** raises `KeyError(ticket_id)` when no row was updated (unknown id).

### How I tested it
- The repo already had tests for every behaviour in the issue (`tests/test_users.py`, `tests/test_tickets.py`), so I didn't add new ones.
- In a copy of the repo I ran `make setup && pytest`: **33 passed**. Without the code change, the same setup gives **19 failed, 14 passed**, which confirms the tests cover the bugs.

### Side effects / things for the reviewer
- **`make setup` destroys the committed dev database.** `scripts/reset_fixtures.py` deletes every row in `users` in `data/dev.db` (it reported "dropped 1204 rows") and seeds 8 fixture users. The roughly 3,180 tickets are left pointing at users that no longer exist. Setup also applies migrations 0003 and 0004, which changes that tracked file. The tests depend on those fixtures, so following the README as written overwrites the sample data. That's why I ran it in a copy. A follow-up should point the tests and fixtures at a separate DB, such as a temp file or one set by an env var.
- **Behaviour changes for callers:** code that relied on `create` allowing duplicates, `add` accepting blank subjects, or `close` silently ignoring unknown ids will now get exceptions.
- **No database-level uniqueness yet.** The duplicate check runs in application code, so two signups at the same moment could still both get through. A unique index on `lower(email)` would close that gap, but it would fail on any existing database that already has case-only duplicates, so I left it out of this PR.

Nothing is committed; only the two source files are modified.