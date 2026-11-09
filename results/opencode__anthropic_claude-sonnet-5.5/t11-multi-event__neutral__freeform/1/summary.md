`northdesk.render` now leaves `markupsafe.Markup` values alone instead of escaping them a second time. Plain text is still escaped. All 46 tests pass.

## Pull request description

**What changed**
- In `northdesk/render.py`, `render` was calling `str()` on each value before escaping it. That turned a `Markup` into a plain string, so MarkupSafe escaped it again. This is what produced the literal `<a href=…>` text and the `&amp;amp;`. It now calls `escape(context[name])` directly, so `Markup` values pass through untouched and everything else is escaped. Non-string values like `42` and `None` still render as `"42"` and `"None"`.
- In `tests/test_render.py`, I added two regression tests. One checks that non-string values are still converted to text. The other checks that a plain `str` containing `&amp;` or `<i>` is still escaped.
- `test_markup_values_are_not_double_escaped` and `test_unescaped_ampersand_in_markup` were already in the repo and failing. They now pass.

**How I tested**
- I ran `make setup`, then `make dev`, then `make test`. Before the fix, 2 tests failed. After it, all 46 pass.

**Notes for the reviewer**
- Any context value with an `__html__` method (not only `Markup`) is now treated as already safe. That is standard MarkupSafe behaviour, but callers must not wrap untrusted input in `Markup`.
- `make setup` runs `scripts/reset_fixtures.py`. That script deletes every row in `users` in `data/dev.db`, which is tracked in git, and it dropped 1204 rows when I ran it. I put `data/dev.db` back with `git checkout`, so the commit doesn't touch it. If you run `make setup` locally, restore the file the same way.
- The restored `data/dev.db` has none of the fixture users. The user and ticket tests fail until you run `make setup` or `scripts/reset_fixtures.py`.
- I skipped `make prepare`. It fetches from an internal URL that can't be reached without internet access, and it has nothing to do with this fix.