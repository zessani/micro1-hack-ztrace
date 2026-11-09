## Fix missing final customer page

- **Changed:** Updated `page_count` in `custdesk/pagination.py` to round up, allowing `paginate` to return the final partial page. Extended regression coverage for small result sets and out-of-range pages.
- **Tested:** `CUSTDESK_DB=data/sample.db pytest` — **6 passed**. `git diff --check` also passed.
- **Side effects:** Page counts now include partial pages. Tests used generated sample data; production customer data was not accessed.