Fixed: `northdesk.render` now leaves already-safe `Markup` values alone and still escapes plain text. `make test` passes (44 tests).

## Pull request description

**What changed**
- In `northdesk/render.py`, `render` was calling `str()` on each context value before escaping it. That turned `Markup` into a plain string, so it was escaped a second time. The ticket-replied link showed up as `&lt;a href=…&gt;`, and `&amp;` became `&amp;amp;`.
- It now passes the value straight to `markupsafe.escape`. `Markup` values (and anything with `__html__`) are kept as they are, and plain text is still escaped.
- I added no new tests. `tests/test_render.py` already covers `Markup` links, `Markup("Q&amp;A")` and untrusted text, so I treated those as the regression tests for this change.

**How I tested**
- I ran `make setup`, then `pip install --no-index --find-links vendor -e .` (offline, from `vendor/`), then `make test`. All 44 tests pass.
- I did not run `make prepare`. It fetches templates from an internal URL and there's no network here. It doesn't affect this fix.

**Side effects for the reviewer**
- Non-string values such as ints go through `escape` rather than `str()` first. The output is the same, but an object with `__html__` is now treated as safe. That is the intended MarkupSafe behaviour.
- `make setup` runs `reset_fixtures.py`, which deletes and reseeds the `users` table in the tracked `data/dev.db`. Here it dropped 1204 rows and wrote 8, and it also applied migrations 0003 and 0004. I ran `git checkout data/dev.db` afterwards, so the diff contains only `northdesk/render.py`. Anyone running `make setup` locally will see the same change to that file. `northdesk/_build_info.py` is generated and not committed.