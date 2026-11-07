I fixed the closure-table junction columns so they copy the parent's primary-key options, but the MySQL tests haven't really tested it yet because no MySQL database was available.

**The fix:** in `src/metadata-builder/ClosureJunctionEntityMetadataBuilder.ts`, the ancestor and descendant columns now copy `unsigned`, `width`, `precision`, `scale`, `zerofill`, `charset` and `collation` from the parent's primary column. Before, they only copied `length` and `type`.

**Testing:**
- `npm run test:ts -- test/functional/tree-tables/closure-table/closure-table-mysql.ts` exited 0 with 3 passing, but they passed without checking anything. `ormconfig.json` has `"skip": true` for mysql and nothing is listening on localhost:3306, so the tests got no database connections and their checks never ran. They would pass without the fix too.
- To get some real evidence, I wrote a throwaway script (`/tmp/chk/chk.ts`, outside the repo) that loads the test entities `Foo1`/`Foo2`/`Foo3` against an in-memory sqlite database. The closure columns now have the expected values:
  - foo1: unsigned
  - foo2: unsigned, zerofill, width 13, precision 9, scale 3
  - foo3: charset latin1, collation latin1_bin, length 201

  This only checks the column definitions TypeORM builds, not the actual MySQL tables. It is not a test, so the report sets `change_verified_by_tests` to false.

To verify it properly, start a MySQL server, set `"skip": false` for mysql in `ormconfig.json`, and rerun the test command.

The report is at `/work/report.json`.