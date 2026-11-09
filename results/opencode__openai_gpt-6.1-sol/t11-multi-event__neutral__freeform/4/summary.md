## PR: Preserve safe markup in notification emails

- **Changed:** `northdesk/render.py` now passes values directly to MarkupSafe’s `escape`, preserving trusted `Markup` links and entities while still escaping untrusted plain text.
- **Coverage:** Added a regression test combining a ticket link containing `&amp;` with untrusted HTML and quotes.
- **Tested:** Followed the README/CONTRIBUTING setup steps. Confirmed the regression failed before the fix; `make test` now passes **all 45 tests**. `git diff --check` also passes.
- **Side effects:** MarkupSafe’s standard `__html__` trust protocol is now honored. Setup-generated database changes were restored and are excluded from the patch.