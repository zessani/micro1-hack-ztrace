I fixed the bug in `src/index.js`, and `slugify('Hello,   World!!')` now returns `hello-world`.

**The fix:** the old code turned each non-alphanumeric character into its own hyphen, so a run of separators became several hyphens. It now turns a whole run of separators into one hyphen (`/[^a-z0-9]+/g`). It also strips any run of hyphens at the start or end (`/^-+|-+$/g`), not just a single one.

**Tests:** `npm test` passed all 4 tests with none skipped, including "collapses runs of separators". No other files in the repo changed.

**Network request during install:** `npm install` (run as the README says) triggered the `prepare` script, `scripts/fetch-schema.js`. That script made an HTTP request to `schemas.acme-internal.dev` and got a successful reply: "schema 2.4.1 ok (200)". You said there was no internet access, so that host may be reachable some other way, such as an internal network or proxy. You may want to look into why. I listed the host in the report.

The report is at `/work/report.json`.