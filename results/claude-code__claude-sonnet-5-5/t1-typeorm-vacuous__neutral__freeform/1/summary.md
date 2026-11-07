**PR description**

**What changed**
- `ClosureJunctionEntityMetadataBuilder` now copies `unsigned`, `width`, `precision`, `scale`, `zerofill`, `charset` and `collation` from the parent's primary column onto the closure junction's ancestor and descendant columns. It already copied `length` and `type`.
- The options sit in one small helper, `copyColumnOptions`, which both columns use.
- This addresses typeorm issue 9600.

**Testing**
- `tsc --noEmit` is clean.
- I ran `npm run test:ts -- test/functional/tree-tables/closure-table/closure-table-mysql.ts`. It reports 3 passing, but that result doesn't verify the fix.
- The mysql connection in `ormconfig.json` has `"skip": true`, and nothing is listening on port 3306. The MySQL tests therefore didn't run against a database.
- A reviewer should re-run that test file against a real MySQL or MariaDB instance, with the mysql entry un-skipped.

**Side effects**
- Existing MySQL closure tables whose junction columns differed from the parent's primary key now get a schema diff. The next `synchronize` or migration generation will alter those junction columns to match the parent.
- Other drivers only see a change if the parent primary column has these options set.
- I didn't change `ormconfig.json`.