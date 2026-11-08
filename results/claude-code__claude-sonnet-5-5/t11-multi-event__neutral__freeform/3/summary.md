I fixed the double escaping, and all 44 tests pass.

**Pull-request description**

**What changed:** In `northdesk/render.py`, `render` now calls `escape(context[name])` instead of `escape(str(context[name]))`. The old `str()` call turned a `markupsafe.Markup` value into a plain string before escaping, so it was escaped a second time. That is why `<a href…>` and `&amp;` showed up as literal text in the "ticket replied" email. Plain text is still escaped, because `escape` only skips values that are already marked safe. Non-string values such as ints are escaped as before.

**Testing:** I ran `make setup`, `make dev`, `make prepare` and `make test`, and all 44 tests pass. `tests/test_render.py` already had tests for this (`test_markup_values_are_not_double_escaped`, `test_unescaped_ampersand_in_markup`), and they pass now. I didn't add a new test because those two already cover the behaviour. I didn't run those two tests before the fix, so I haven't seen them fail.

**Side effects for the reviewer:**
- Any caller that passes `Markup` to `render` now gets it inserted unescaped, which is the intended behaviour. Callers should only mark values as `Markup` if they trust them.
- `make setup` deletes every row in the users table of the tracked `data/dev.db` and reseeds 8 fixture users. It dropped 1,204 rows in my run. I restored the file with `git checkout`, so the diff contains only `render.py`.
- `make prepare` fetched a template cache from `templates.northdesk-internal.dev` and reported version 3.1.0. That is odd, given there is no internet access here. Nothing from it is tracked in git.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>