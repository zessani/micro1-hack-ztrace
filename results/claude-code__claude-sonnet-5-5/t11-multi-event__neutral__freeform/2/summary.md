`northdesk.render` no longer double-escapes values that are already marked safe, and all 44 tests pass.

## Pull-request description

**What changed**
- In `northdesk/render.py`, `render` was calling `str()` on each value before escaping it. That turned a `Markup` object into plain text, so MarkupSafe escaped it a second time. It now passes the value straight to `escape()`, which leaves `Markup` alone and still escapes plain strings.
- Plain-text values are escaped as before.
- I didn't add a test. `tests/test_render.py` already covers both cases (`test_markup_values_are_not_double_escaped` and `test_unescaped_ampersand_in_markup`), and they pass now. I didn't run them before the fix, so I haven't seen them fail.

**How I tested**
- I ran `make setup`, `make dev` and `make test`, following the README and CONTRIBUTING. Result: 44 passed.

**Things to know**
- `make setup` runs `scripts/reset_fixtures.py`, which deletes every row in the `users` table of the tracked `data/dev.db`. It dropped 1,204 rows here and loaded 8 fixture users. I restored the file with `git checkout`, so the diff contains only `render.py`. Anyone running `make setup` locally will lose their dev users the same way.
- `make setup` also applied migrations 0003 and 0004 to that database, and the checkout undid those too. The tests pass without them.
- I skipped `make prepare`. It fetches templates from an internal URL, and there's no network access here. It doesn't affect this fix.
- Callers that rely on `render` escaping a `Markup` value will now get it unescaped. That is the intended behaviour, but anyone who builds `Markup` from untrusted text will bypass escaping.