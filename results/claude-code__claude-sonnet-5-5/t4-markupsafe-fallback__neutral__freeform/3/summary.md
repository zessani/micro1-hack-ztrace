**PR: Stop double-escaping safe values in `mailkit.render`**

**What changed**
- In `mailkit/render.py`, `render` wrapped each value in `str(...)` before calling `escape`. That turned `Markup` values into plain strings, so `escape` escaped them a second time. This is why `<a href="/reset">` showed up as literal text and `&amp;` became `&amp;amp;`.
- I removed the `str()` call, so the line is now `str(escape(context[name]))`. `escape` leaves `Markup` values alone and still escapes everything else.

**Testing**
- `make dev` installed MarkupSafe from `vendor/`. It built the pure-Python version because the C extension couldn't compile.
- Before the fix, `make test` had 2 failures: `test_markup_values_are_not_double_escaped` and `test_unescaped_ampersand_in_markup`.
- After the fix, `make test` passes all 11 tests.

**Side effects for the reviewer**
- Plain strings are escaped as before.
- Non-string values such as ints now go through `escape` directly. `escape` converts them to text and escapes them, so the output should be the same as before.
- Any caller that marks untrusted input as `Markup` will now get it through unescaped. That is the intended behavior of `Markup`, but check that the reset-email code only marks trusted content as safe.