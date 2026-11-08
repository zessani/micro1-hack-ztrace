## PR: Fix double-escaping in ticket notification emails

**Changed:** `northdesk/render.py` now passes values directly to MarkupSafe’s `escape`, preserving trusted `Markup` links and entities while continuing to escape untrusted plain text. Added regression coverage for both in the same email.

**Tested:** Followed README/CONTRIBUTING setup steps. Confirmed failures before the fix; `make test` now passes all **45 tests**. `git diff --check` passes.

**Side effects:** MarkupSafe’s standard `__html__` protocol is now honored. Setup-generated database changes were reverted; only the renderer and test file are changed.