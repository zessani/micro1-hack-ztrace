**PR description**

**What changed**
- In `northdesk/render.py`, `render` no longer calls `str()` on a value before escaping it. That call turned `markupsafe.Markup` values into plain strings, so `escape` escaped them a second time. Values are now passed straight to `escape`. `Markup` values (and anything with `__html__`) are left alone, and plain text is still escaped.
- In `tests/test_render.py`, I added a test that mixes a `Markup` link with untrusted text. I also added one for non-string values such as `42`.

**How I tested**
- I followed the README and CONTRIBUTING: `make setup`, then `make dev`, then `make test`.
- Before the fix, 2 tests failed: `test_markup_values_are_not_double_escaped` and `test_unescaped_ampersand_in_markup`. After it, all 46 pass.
- I didn't run `make prepare`. It tries to fetch templates from an internal host, and there's no network here. It isn't needed for the tests.

**Side effects for the reviewer**
- Behaviour only changes for `Markup` or `__html__` values, which are no longer escaped twice. Plain strings and numbers render as before. Anyone who passed `Markup` expecting it to be escaped again will see different output.
- Callers must only wrap trusted content in `Markup`. Anything marked safe is now emitted as-is.
- `make setup` runs `scripts/reset_fixtures.py`, which deleted 1204 users from the tracked `data/dev.db` and seeded 8 fixture users. It also applied migrations 0003 and 0004. I ran `git checkout data/dev.db` afterwards, so that file isn't part of this change. Running `make setup` again will modify it.
- `northdesk/_build_info.py` is generated and gitignored, so it isn't committed.