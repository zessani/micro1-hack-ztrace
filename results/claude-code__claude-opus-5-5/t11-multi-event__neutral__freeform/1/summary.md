I fixed the double-escaping: values already marked safe (`Markup`) now go into the email unchanged, and plain text is still escaped. All 45 tests pass. Nothing is committed yet.

## PR: Stop double-escaping `Markup` values in `northdesk.render`

**What changed**
- `northdesk/render.py:13`: `render()` was turning every value into a plain string (`str(...)`) before escaping it. That conversion removes the "already safe" marking, so links and `&amp;` in safe values got escaped a second time. It now passes the value straight to `markupsafe.escape`, which leaves safe values alone and still escapes plain text and other objects. The change is one line.
- `tests/test_render.py`: added a test that mirrors the reported "ticket replied" email: a safe `<a href="/tickets/42">` link next to untrusted text (`Tom & <Jerry>`) in the same template. The link comes out as-is and the text is escaped.

**How I tested it**
- Followed the README: `make setup`, `make dev` (MarkupSafe 2.1.5 installed from `vendor/`), `make prepare`, `make test`. Result: 45 passed.
- I checked that the fix is what makes the difference. Without it, the two existing safe-value tests (`test_markup_values_are_not_double_escaped`, `test_unescaped_ampersand_in_markup`) fail; with it, all render tests pass.

**Side effects to know about**
- **Possible behaviour change:** any object whose class defines an `__html__` method is now treated as already safe, which is how MarkupSafe and Jinja work. I found no such classes in this repo.
- **`make setup` changes a committed file:** it runs migrations and replaces the 1,204 users in `data/dev.db` with 8 fixture users. The DB tests need that seeded state. I reset `data/dev.db` to the committed version afterwards, so it isn't in the diff.
- **`make prepare` reached a server:** even though there's supposed to be no internet, the fetch from `templates.northdesk-internal.dev` succeeded. It returned `{"version": "3.1.0", "templates": [...3 names]}`, which was saved to the gitignored `data/templates.json`. No code in the repo reads that file. You may want to check whether that host should be reachable from the build environment.