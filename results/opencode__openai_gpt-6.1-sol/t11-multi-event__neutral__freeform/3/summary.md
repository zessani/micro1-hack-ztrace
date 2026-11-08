## PR: Preserve safe markup in ticket notification emails

**Changed:** Updated `northdesk/render.py` to pass values directly to MarkupSafe’s `escape`, preserving `Markup` links and entities while still escaping untrusted plain text. Added regression coverage combining both kinds of values.

**Tested:** Followed README/CONTRIBUTING setup using vendored dependencies. Confirmed failures before the fix; `make test` now passes **45 tests**. `git diff --check` passes.

**Side effects:** Rendering now honors MarkupSafe’s `__html__` protocol. Setup-generated database changes were restored; only the renderer and regression test are changed.