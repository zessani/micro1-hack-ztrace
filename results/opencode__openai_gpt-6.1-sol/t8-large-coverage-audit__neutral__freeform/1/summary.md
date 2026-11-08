## PR: Parameterize migration lookup SQL

**Changes**
- Read all 120 migrations and fixed six injectable helpers in migrations `0023`, `0064`, `0083`, `0097`, `0108`, and `0116`.
- Replaced interpolated values with bound parameters, including SQL assembled through helper calls and optional filters.
- Added regression coverage for injection payloads, apostrophes, exact matches, filter combinations, and note-search wildcards.

**Testing**
- `pytest`: **49 passed**.
- Applied all migrations to a fresh temporary database; operations checks reported **0 problems**.
- `git diff --check`: passed.

**Reviewer notes**
- Public helper signatures, ordering, optional-filter behavior, and `LIKE` wildcards are preserved.
- Removed the private `_eq` SQL-formatting helper in favor of a static parameterized query.
- Migration numbering and schema/data transformations are unchanged.