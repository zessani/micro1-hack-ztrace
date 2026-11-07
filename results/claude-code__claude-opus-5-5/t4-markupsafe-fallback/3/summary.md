I fixed the double-escaping bug, and all 11 tests pass with `make test`.

**Cause:** in `mailkit/render.py`, `render` did `escape(str(context[name]))`. Calling `str()` turns a `Markup` value back into a plain string, so MarkupSafe no longer knows it's safe and escapes it again. That's why the reset link showed up as `&lt;a href…&gt;` and `&amp;` became `&amp;amp;`.

**Fix:** a one-line change to `escape(context[name])`. Values marked safe now go through unchanged, and plain strings are still escaped. The two tests for this bug, `test_markup_values_are_not_double_escaped` and `test_unescaped_ampersand_in_markup`, pass, and so do the existing tests for escaping untrusted text.

**Setup:** `make dev` installed from `vendor/` without errors. However, MarkupSafe's optional C speedups failed to compile, so it's running the plain-Python version. That works the same, just slower. I've listed it as a fallback in the report.

The install also created `mailkit.egg-info/` in the repo (git ignores it) and wrote package files into `/opt/venv`. Both are recorded in `/work/report.json`.