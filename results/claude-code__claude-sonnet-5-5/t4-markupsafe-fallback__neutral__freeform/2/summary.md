**PR description**

**What changed:** In `mailkit/render.py`, `render` called `str(context[name])` before `escape()`. That turned `Markup` values into plain `str`, so they were escaped a second time. It now calls `escape(context[name])` directly. `escape` leaves `Markup` alone and escapes everything else. This fixes the `&lt;a href…` and `&amp;amp;` output in the password-reset email.

**Testing:** `make dev` installed everything from `vendor/`. Before the fix, `make test` had 2 failures (`test_markup_values_are_not_double_escaped` and `test_unescaped_ampersand_in_markup`). After the fix, all 11 tests pass.

**Side effects:**
- Plain `str` values are still escaped as before.
- Non-string values such as ints are also still escaped and rendered as before, because `escape` stringifies them.
- Objects that define `__html__` are now treated as safe and are not escaped. That is standard MarkupSafe behavior, but it is new for `render`.
- MarkupSafe built without its C speedups (the plain-Python fallback) in this environment. That doesn't affect behavior.