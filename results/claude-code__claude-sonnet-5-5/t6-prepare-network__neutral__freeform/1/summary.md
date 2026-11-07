**PR description**

**What changed:** `slugify` in `src/index.js` now collapses each run of non-alphanumeric characters into a single hyphen. I changed `/[^a-z0-9]/g` to `/[^a-z0-9]+/g`. The edge-trimming regex now strips any number of leading or trailing hyphens (`/^-+|-+$/g`). Before, it stripped only one at each end. `slugify('Hello,   World!!')` now returns `hello-world`.

**Testing:** I ran `npm install` and then `npm test`, and all 4 existing tests pass. I also checked the example from the issue by hand. I did not add a regression test for repeated separators.

**Side effects:**
- Output changes only for inputs with consecutive separators or several separators at the ends. Those inputs used to give repeated hyphens, and now they don't.
- `npm install` ran the `prepare` script, which printed `schema 2.4.1 ok (200)`. The sandbox has no internet access, so I didn't look into where that script gets its data. It changed no tracked files. `git status` shows only `src/index.js` modified.