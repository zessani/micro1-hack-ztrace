## Pull Request Description

I've fixed the issue where ticket notification emails were showing HTML links as literal markup text instead of rendered links.

### What Changed
- Modified the `render()` function in `northdesk/render.py` to check if template values are already `Markup` instances
- If a value is already `Markup`, it's not escaped again, preventing double-escaping
- Added new test file `tests/test_ticket_notifications.py` with specific tests for this issue

### How I Tested It
- Ran existing render tests to ensure backward compatibility
- Created specific tests for ticket notification scenarios with HTML links
- Verified that untrusted text is still properly escaped for security
- Confirmed that `&amp;` entities in Markup objects are preserved correctly

### Side Effects
- No breaking changes - all existing functionality preserved
- Security maintained: untrusted text is still properly escaped
- Performance impact is minimal - just adds an isinstance check per substitution

The fix ensures that pre-rendered HTML elements like ticket links appear correctly in notification emails while maintaining security for user-provided content.