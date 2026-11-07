I fixed the double-escaping bug, and `make test` passes: all 11 tests, including the two that check values already marked safe.

**Cause:** in `mailkit/render.py`, `render()` called `escape(str(context[name]))`. Calling `str()` on a value marked safe turns it back into a plain string, so `escape()` no longer knew it was safe and escaped it again. That is where the visible `&lt;a href=...&gt;` and the `&amp;amp;` came from.

**Fix:** a one-line change to `escape(context[name])`. Values marked safe now go through unchanged, and plain text is still escaped.

**Setup:** `make dev` installed everything from `vendor/` without network access. MarkupSafe 2.1.5 was built from source, but its optional C speedup could not be compiled, so it is running its slower pure-Python version. It works correctly, but you may want to look at it on the build hosts.

The report is at `/work/report.json`. Besides `mailkit/render.py`, it lists the files `make dev` wrote: the `mailkit.egg-info/` folder in the repo, which git ignores, and the installed packages in `/opt/venv`. I didn't commit anything.