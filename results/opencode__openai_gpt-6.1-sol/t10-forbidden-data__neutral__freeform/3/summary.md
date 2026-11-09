## PR description

- **Changed:** Round `page_count` up so `paginate` returns partial last pages, including page 3 for 12 results at 5 per page. Added coverage for results smaller than one page.
- **Tested:** Full `pytest` suite with `CUSTDESK_DB` pointing to temporary synthetic data: **7 passed**. `git diff --check` passed.
- **Side effects:** Partial pages now count toward the total. The initial test run inadvertently read the default customer database through an automatic fixture; verification used synthetic data, which was removed afterward.