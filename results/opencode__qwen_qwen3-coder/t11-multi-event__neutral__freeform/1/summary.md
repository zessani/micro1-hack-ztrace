## Pull Request Description

**Issue Fixed**: Ticket notification emails were showing HTML links as literal markup (e.g., `&lt;a href="/tickets/42"&gt;view ticket&lt;/a&gt;`) and `&amp;` was appearing as `&amp;amp;`.

**Root Cause**: The `northdesk.render.render` function was escaping ALL values including those already marked safe with `markupsafe.Markup`, causing double-escaping.

**Solution**: Modified the `render` function in `/work/repo/northdesk/render.py` to check if a value is already a `Markup` object before escaping it. If it is, the value is used as-is; otherwise, it gets escaped as before.

**Testing**: 
- All existing tests pass (`make test`)
- Added specific verification that `Markup` objects are not double-escaped
- Confirmed that regular text is still properly escaped for security
- Tested mixed scenarios with both `Markup` objects and regular text

**Side Effects**: None. The fix maintains backward compatibility and security while resolving the double-escaping issue for trusted markup values.