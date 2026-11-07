**PR description**

**What changed:** In `mailkit/render.py`, `render` called `escape(str(context[name]))`. The `str()` turned `Markup` values into plain strings, so `escape` escaped them a second time. It now calls `escape(context[name])`. `Markup` values are left as they are, and all other values are still escaped.

**Testing:** I ran `make dev`, which installed from `vendor/`. Before the fix, `make test` had 2 failures, `test_markup_values_are_not_double_escaped` and `test_unescaped_ampersand_in_markup`. After the fix, all 11 tests pass.

**Side effects:**
- Non-string values such as ints or `None` are now passed straight to `escape`. It stringifies them itself, so the output should be the same as before. No test covers this.
- Anything that passes `Markup` to `render` now gets it unescaped, which is the intended behavior. Callers should only wrap trusted content in `Markup`.
- MarkupSafe built without its C speedups during `make dev`. That is only a performance matter.