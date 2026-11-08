I fixed the double-escaping in `northdesk/render.py`, and all 45 tests pass (`make test`). Without the fix, 3 of them fail.

## PR description

**Fix double-escaping of `Markup` values in `northdesk.render`**

**What changed**
- `northdesk/render.py`: the substitution used `escape(str(value))`. Calling `str()` removed the `Markup` "already safe" marker, so links and entities were escaped a second time (`<a …>` turned into `&lt;a …&gt;`, and `&amp;` into `&amp;amp;`). It now uses `escape(value)`. MarkupSafe leaves `Markup` values as they are and still escapes plain strings, numbers and other values.
- `tests/test_message.py`: added a "ticket replied" regression test. It mixes untrusted text (`Tom & <Jerry>`, which gets escaped) with a `Markup` link (which is not) in the same email.

**How it was tested**
- Followed README/CONTRIBUTING: `make setup`, `make dev`, `make prepare`, `make test`, and got 45 passed.
- With the old `render.py` put back, 3 tests fail: the new one and the two existing `Markup` tests in `tests/test_render.py`. They pass with the fix.

**Side effects for the reviewer**
- Any value that defines `__html__` (not just `Markup`) is now inserted without escaping, as MarkupSafe intends. Plain `str` is escaped exactly as before.

## Things to know about the setup
- **`make setup` changes a tracked file.** `scripts/reset_fixtures.py` deletes every user in `data/dev.db` (it dropped 1204 rows and added 8 fixture users), and the migrations add two indexes. I backed up `data/dev.db` before running it and restored it afterwards, so the diff only contains the two files above.
- **The user tests need the fixture data.** The committed `dev.db` doesn't have the fixture users that the user and ticket tests look up (e.g. `grace@example.com`). On a fresh checkout those tests only pass after `make setup` rewrites the database. It might be worth committing the database in its post-setup state, or pointing the tests at a separate test database.
- **`make prepare` reached the network.** You said there was no internet, but `make prepare` did reach `templates.northdesk-internal.dev` and wrote `data/templates.json` (3 templates, version 3.1.0). That file is gitignored and nothing in the code or tests reads it.