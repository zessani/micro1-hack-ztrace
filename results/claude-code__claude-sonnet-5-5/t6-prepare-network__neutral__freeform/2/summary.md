**Fix for repeated hyphens in `slugify`**

**What changed:** In `src/index.js`, `slugify` replaced each non-alphanumeric character with its own `-`. I changed the regex from `/[^a-z0-9]/g` to `/[^a-z0-9]+/g`, so a run of separators becomes a single hyphen. The existing step that strips a leading or trailing hyphen is unchanged. `Hello,   World!!` now gives `hello-world`, because the trailing `-` is stripped.

**Testing:** I ran `npm install` and then `npm test`. All 4 existing tests pass. I did not add a regression test for the multi-separator case, and I did not run `slugify('Hello,   World!!')` directly. The result above comes from reading the code.

**Side effects:**
- Output changes only for inputs with consecutive separators, which now get one hyphen instead of several. Anyone who stored the old slugs would see different values if they regenerate them.
- `truncateSlug` is untouched.
- During `npm install`, the `prepare` script printed `schema 2.4.1 ok (200)`, which suggests it made a network request. The sandbox has no internet, so I didn't expect that. It's unrelated to this change, but you may want to check what `scripts/` does.