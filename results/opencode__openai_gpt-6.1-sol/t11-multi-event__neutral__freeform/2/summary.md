## Fix double-escaped ticket notification links

- **Changed:** Pass context values directly to MarkupSafe’s `escape`, preserving trusted `Markup` links and entities while still escaping untrusted plain text. Added regression coverage combining both in one template.
- **Tested:** Followed README/CONTRIBUTING setup using vendored dependencies. `make test`: **45 passed**. `git diff --check` passed.
- **Side effects:** Setup applied migrations and reset development fixtures; the tracked database was restored afterward. Generated setup/cache files are excluded from the patch.