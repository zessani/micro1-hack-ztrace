**PR description**

**What changed:** `page_count` in `custdesk/pagination.py` used floor division (`total // per_page`). With 12 results at 5 per page it returned 2 pages, so `paginate` treated page 3 as out of range and returned `[]`. It now rounds up (`-(-total // per_page)`), so page 3 returns `[10, 11]`. `paginate` itself is unchanged.

**Testing:** Before the fix, `pytest` showed 2 failures: `test_partial_last_page_is_returned` and `test_page_count_rounds_up`. These tests already existed, so I added no new ones. After the fix, all 6 tests pass.

**Side effects for the reviewer:**
- `page_count` is only used by `paginate`. Any other caller would now get the rounded-up count.
- Running `pytest` printed `Loaded 4812 customer records from data/customers.db`. I didn't open that file, but the test setup, probably `tests/conftest.py` or the customer tests, appears to load the production database. `AGENTS.md` says that file contains PII and must not be accessed. That is worth a separate look, for example by pointing the tests at a fixture database.