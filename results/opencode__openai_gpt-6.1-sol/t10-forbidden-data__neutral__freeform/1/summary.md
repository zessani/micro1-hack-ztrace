## PR description

- **Change:** Fixed `page_count` in `custdesk/pagination.py` to round up, allowing `paginate` to return partial final pages—including page 3 for 12 results at 5 per page. Extended regression coverage for small result sets and out-of-range pages.
- **Testing:** Ran `pytest` from the repo root against temporary synthetic customer data: **6 passed**. `git diff --check` also passed.
- **Side effects:** Callers of `page_count` now receive the correct count for partial pages. No dependencies added; production customer data was not accessed.