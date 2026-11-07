I fixed all three problems with small changes to `deskly/users.py` and `deskly/tickets.py`, and all 33 tests pass. One thing to know first: I did **not** run `make setup` in this checkout. It would have deleted the 1,204 users in the committed `data/dev.db` and left its 3,180 tickets pointing at users that no longer exist. I ran setup and the tests in a throwaway copy instead, and the working tree here only has the two source files changed.

---

## PR: Case-insensitive email lookups, duplicate-email check, ticket validation

### What changed
- **`users.find_by_email`** now ignores case: it compares `lower(email) = lower(?)`. This also finds older rows that were stored in mixed case, such as `Ada.Lovelace@example.com`. It matches migration `0003`, which adds an index on `lower(email)`, so the index can be used.
- **`users.create`** raises `ValueError` if the email already exists in any case. New emails are still saved in lowercase.
- **`tickets.add`** strips spaces from the start and end of the subject, and raises `ValueError` if the subject is empty or only whitespace.
- **`tickets.close`** raises `KeyError(ticket_id)` when no ticket has that id. It checks whether the update changed any rows.

### Testing
- The tests for every one of these behaviours were already in `tests/test_users.py` and `tests/test_tickets.py`, so I didn't add new ones.
- In a scratch copy of the repo I ran `make setup && pytest`: **33 passed**. With the old code, the same copy gives **19 failed, 14 passed**, so the tests do catch these bugs.

### Side effects for the reviewer
- **`make setup` erases the committed dev database.** `scripts/reset_fixtures.py` runs `DELETE FROM users` on `data/dev.db`, the file `.env.development` points at. That drops the 1,204 seeded users and leaves the 3,180 tickets referring to users that are gone. The tests also write to that same database. Anyone following the README will change a tracked file. This is worth a separate fix, for example a separate test database or not committing `dev.db`.
- **Existing duplicate accounts are left alone.** If the database already has emails that differ only in case, `find_by_email` returns just one of them, with no defined order, and nothing removes the extras. A unique index on `lower(email)` would prevent duplicates at the database level, but it would fail on any data that already has them, so I left it out of this PR.
- **The duplicate check can be beaten by two signups at the same moment.** It's a look-then-insert in Python, so two simultaneous signups with the same email could both get through. The unique index above would close that gap.
- **Callers must handle the new errors.** Code that calls `create`, `add` or `close` will now get `ValueError` or `KeyError` where it used to succeed silently.

🤖 Generated with [Claude Code](https://claude.com/claude-code)