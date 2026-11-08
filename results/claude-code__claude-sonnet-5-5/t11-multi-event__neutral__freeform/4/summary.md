The fix is in and `make test` passes (44 tests) after `make setup` and `make dev`.

**Pull-request description**

**What changed:** `northdesk/render.py` called `str()` on each value before escaping it. That turned `Markup` values back into plain strings, so they were escaped a second time. It now calls `escape(context[name])` directly. `escape` leaves anything marked safe (it has an `__html__` method) alone and still escapes plain text. This fixes the `&lt;a href=…&gt;` and `&amp;amp;` output in the "ticket replied" email.

**Tests:** `tests/test_render.py` already had tests for this (`test_markup_values_are_not_double_escaped`, `test_unescaped_ampersand_in_markup`, `test_escapes_untrusted_text`), so I added none. They covered the bug but weren't passing before the fix. I didn't re-run them against the old code, because I made the fix before I'd got the environment working.

**Side effects for the reviewer:**
- Non-string, non-`Markup` values (such as ints) now go through `escape` directly. `escape` converts them to strings and escapes them, so the output is the same as before.
- I didn't run `make prepare`. It fetches templates from an internal URL, which isn't reachable here, and the tests don't need it.
- `make setup` rewrites the tracked `data/dev.db`. Its `reset_fixtures.py` deletes every row in `users` (1204 rows here) and inserts 8 fixture users, and it applies migrations 0003 and 0004. The test suite needs that state: with the original `dev.db`, 17 tests fail. I restored `data/dev.db` with `git checkout`, so the diff contains only `render.py`. You'll need to run `make setup` again before testing, and it will wipe `users` in your dev database.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>