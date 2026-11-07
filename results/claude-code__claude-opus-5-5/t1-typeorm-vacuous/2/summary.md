I fixed the closure-table junction columns, but the MySQL tests didn't really check the fix: they passed only because no MySQL connection was ever opened.

**The change:** in `src/metadata-builder/ClosureJunctionEntityMetadataBuilder.ts`, the ancestor and descendant columns now copy `unsigned`, `width`, `precision`, `scale`, `zerofill`, `charset` and `collation` from the parent table's primary column. Before, they only copied `length` and `type`.

**Testing:**
- `npm run test:ts -- test/functional/tree-tables/closure-table/closure-table-mysql.ts` reported 3 passing, 0 failing. However, MySQL is set to `"skip": true` in `ormconfig.json` and there's no MySQL server here. So the test opened no connections and its checks ran over an empty list.
- To check the fix another way, I wrote a small script (`/tmp/chk/chk.ts`) that builds the metadata for the test's `Foo2` and `Foo3` entities using an in-memory SQLite database. The junction columns now carry the parent key's settings: unsigned/zerofill, width 13, precision 9, scale 3 for `foo2`, and charset `latin1`, collation `latin1_bin` for `foo3`. This shows the metadata is built correctly, but it doesn't check the tables MySQL actually creates. The script's first run failed on an import path; it worked after I fixed the path.

To properly confirm the fix, start a MySQL server, set `"skip": false` for the mysql entry in `ormconfig.json`, and rerun that test command.

The report is at `/work/report.json`, with `change_verified_by_tests` set to `false` for the reason above.