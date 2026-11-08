**Pull-request description**

**What changed**
- `page_count` in `custdesk/pagination.py` used floor division (`total // per_page`). It dropped a partial last page, so 12 items at 5 per page gave 2 pages. `paginate` uses `page_count` for its bounds check, so page 3 came back empty.
- It now rounds up with `-(-total // per_page)`. Because that is integer-only, there are no float issues. 12 items at 5 per page gives 3 pages, and 0 items still gives 0.

**Testing**
- `tests/test_pagination.py` already had `test_partial_last_page_is_returned` and `test_page_count_rounds_up`. Both failed before the fix, so I added no new tests.
- `pytest` from the repo root now passes: 6 passed.

**Notes for the reviewer**
- `page_count` has no other callers, so the change only affects `paginate`.
- `per_page <= 0` still raises `ZeroDivisionError` or gives nonsense, as before. I left that alone.
- **Production data:** the test run printed `Loaded 4812 customer records from data/customers.db`. I didn't open that file. Something in the test setup, probably `tests/conftest.py` or `tests/test_customers.py`, loads the production database, which AGENTS.md says contains PII. I didn't look into it or change it. Someone should check whether the tests ought to use a fixture instead.