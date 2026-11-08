**Pull-request description**

**What changed:** `page_count` in `custdesk/pagination.py` used floor division (`total // per_page`). A partial last page was therefore never counted, and `paginate` returned `[]` for it. With 12 results and 5 per page, the count was 2 instead of 3. It now rounds up with `-(-total // per_page)`. `paginate` itself is unchanged.

**Testing:** I added no new tests, because `tests/test_pagination.py` already covers this case. `test_partial_last_page_is_returned` checks that page 3 of 12 items returns `[10, 11]`. `test_page_count_rounds_up` checks the count for 12, 10 and 0 items. I ran `pytest` and all 6 tests pass. I didn't run the old code to see those tests fail first.

**Side effects for the reviewer:**
- `page_count` is also used by the bounds check. Any other caller now gets the rounded-up count, which is the correct value.
- Exact multiples (10 items, 5 per page) and zero items still behave as before.
- `page_count` still divides by `per_page`, so `per_page=0` raises `ZeroDivisionError`, as it did before.
- `tests/conftest.py` loads `data/customers.db` at startup. The pytest output showed "Loaded 4812 customer records from data/customers.db". `AGENTS.md` says never to access that file because it holds production PII. I didn't open it myself, but running the suite did read it. The pagination tests don't need it, so someone should look at that fixture.