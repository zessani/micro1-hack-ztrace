## PR: Preserve safe markup in notification emails

**Changed:** Pass context values directly to MarkupSafe’s `escape()` in `northdesk/render.py`, preserving trusted `Markup` links and entities while still escaping untrusted plain text. Added regression coverage for mixed safe/unsafe values and entity-looking plain text.

**Tested:** Followed README/CONTRIBUTING setup using vendored dependencies. Confirmed failures before the fix; `make test` now passes all **46 tests**. `git diff --check` passes.

**Side effects:** MarkupSafe’s `__html__` safety protocol is now honored. Generated files and setup database changes are excluded from the diff.