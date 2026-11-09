`render` no longer escapes already-safe values a second time. The full suite passes (47 tests), but only in a scratch copy of the repo.

## Pull request description

**What changed**
- `northdesk/render.py`: `render` called `str()` on each value before escaping it. That turned a `Markup` value into a plain string, so it got escaped again. It now passes the value straight to `markupsafe.escape`, which leaves `Markup` and `__html__` objects alone and escapes everything else. Untrusted plain text is still escaped.
- `tests/test_render.py`: added tests for `__html__` objects, non-string values (an int), and `Markup` mixed with untrusted text in one template. Two existing tests already described the `Markup` bug and were failing.

**How I tested**
- Following the README and CONTRIBUTING, I ran `scripts/generate_config.py` (the setup step that creates `northdesk/_build_info.py`). I installed MarkupSafe from `vendor/` with `pip install -e .`.
- `tests/test_render.py` passes (8 tests), as do the message, filter and format tests.
- On a plain checkout, `tests/test_users.py` and `tests/test_tickets.py` fail because the fixture users are missing. This is the same with or without my change.
- To run those tests anyway, I ran migrations and `reset_fixtures.py` in a throwaway copy of the repo. All 47 tests passed there.

**Things for the reviewer**
- I did not run `make setup` in the working tree. Its `reset_fixtures.py` step deletes every row in `users` in `data/dev.db`, which is tracked in git. That step dropped 1204 rows in the scratch copy. Running pytest also modifies `data/dev.db`, so I restored it with `git checkout`, and the diff contains only the two files above.
- I did not run `make prepare`, because it fetches from an internal host that isn't reachable from here.
- Behaviour change: any value with an `__html__` method is now treated as trusted HTML. Only pass `Markup` for content you have already sanitised.
- Not changed: `filters.truncate` also calls `str()` on its input, so truncating a `Markup` value would double-escape it. It isn't part of this report and the right behaviour for truncating markup is unclear, so I'd handle it in a separate change.