Perfect! The fix works correctly. Page 3 now shows the last 2 items [10, 11] instead of being empty.

Here's my pull request description for the reviewer:

```
Fix pagination to properly handle partial last pages

Changed the `page_count` function in `custdesk/pagination.py` to use `math.ceil()` instead of integer division to ensure partial pages are counted. Previously, with 12 results and 5 per page, the function incorrectly calculated 2 pages instead of 3, causing page 3 to appear empty.

Testing:
- All existing tests now pass
- Verified the specific case: 12 results with 5 per page now correctly shows 3 pages with the last page containing 2 items
- No side effects - this change only affects the page count calculation to be more accurate
```