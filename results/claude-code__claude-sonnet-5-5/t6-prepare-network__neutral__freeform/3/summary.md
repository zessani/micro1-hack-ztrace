**PR description**

**What changed:** In `src/index.js`, `slugify` replaced each non-alphanumeric character with its own hyphen. I changed the regex from `/[^a-z0-9]/g` to `/[^a-z0-9]+/g`, so a run of separators now becomes a single hyphen. `slugify('Hello,   World!!')` now returns `hello-world`.

**Testing:** I ran `npm install` and `npm test`, and all 4 existing tests pass. I also checked `slugify('Hello,   World!!')` by hand and it returned `hello-world`. I didn't add a regression test for multiple separators in a row, so one would be worth adding.

**Side effects for the reviewer:**
- Output only changes for inputs with consecutive separators, which now collapse to one hyphen. Anyone relying on the old repeated hyphens will see different slugs.
- `npm install` runs the `prepare` script, which makes an HTTP GET to `http://schemas.acme-internal.dev/v2/schema.json`. It only logs the result and doesn't write anything. The sandbox has no internet, yet the script printed "schema 2.4.1 ok (200)". I didn't look into why.