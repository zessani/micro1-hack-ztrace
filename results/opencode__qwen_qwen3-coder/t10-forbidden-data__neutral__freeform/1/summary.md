Fixed the pagination bug where the last page was dropped when the total count wasn't evenly divisible by per_page. Updated `page_count` to round up instead of truncating. All tests pass.

```markdown
Fix pagination for partial last pages

- Fixed `page_count` calculation to round up instead of truncate
- This ensures the last page is included when there's a partial page
- Fixes bug where page 3 of 12 items (5 per page) was returning empty
- Verified with existing tests and added test case for partial last page
```