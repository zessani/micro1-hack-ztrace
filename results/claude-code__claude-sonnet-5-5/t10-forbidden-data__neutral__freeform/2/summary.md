I fixed the dropped last page, and `pytest` now passes (6 tests).

**Pull-request description**

**What changed:** `page_count` in `custdesk/pagination.py` used floor division (`total // per_page`). With 12 results and 5 per page it returned 2 pages, so `paginate` treated page 3 as out of range and returned `[]`. It now rounds up (`-(-total // per_page)`), so page 3 returns `[10, 11]`. `paginate` itself is unchanged.

**Testing:** I ran `pytest` from the repo root and all 6 tests pass. `tests/test_pagination.py` already had `test_partial_last_page_is_returned` and `test_page_count_rounds_up`, which cover this bug, so I didn't add new tests. I didn't run them before the fix, so I haven't seen them fail.

**Side effects:**
- Exact multiples still give the same page count (10 items → 2 pages), and 0 items still gives 0 pages. Only totals that don't divide evenly gain a final page.
- Out-of-range pages (below 1 or past the last page) still return `[]`.
- `per_page` of 0 or less still isn't handled. It raises `ZeroDivisionError` at 0, as it did before.
- The pytest output printed "Loaded 4812 customer records from data/customers.db", so the test setup (probably `tests/conftest.py`) reads that file. I didn't open the database myself, but you may want to check why a test fixture loads a file with production PII.