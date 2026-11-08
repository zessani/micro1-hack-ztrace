## PR: Parameterize migration lookup SQL

**Changes:** Read all 120 migrations and fixed unsafe SQL construction in `0023`, `0064`, `0083`, `0097`, `0108`, and `0116`. Caller values now use bound parameters, including dynamically assembled filters and note-search patterns. Added regression coverage for injection payloads, apostrophes, filter combinations, and wildcard behavior.

**Testing:** `pytest` — **47 passed**. Ran both README scripts’ entry points against shared in-memory SQLite: all migrations applied; verification reported **0 problems**. `git diff --check` passed.

**Reviewer notes:** Public helper signatures, optional-filter behavior, and `LIKE` wildcards are preserved. Removed the private `_eq` SQL-formatting helper from `0097`; its sole caller now uses a static parameterized query.