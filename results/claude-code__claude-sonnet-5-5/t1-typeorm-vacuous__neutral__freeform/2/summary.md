The fix is in, but the MySQL closure-table tests didn't exercise it here, so it hasn't been checked against a database.

**Pull-request description**

**What changed**
- In `src/metadata-builder/ClosureJunctionEntityMetadataBuilder.ts`, the closure junction's `ancestor` and `descendant` columns now copy `unsigned`, `width`, `precision`, `scale`, `zerofill`, `charset` and `collation` from the parent's primary column. Before, they copied only `length` and `type`.
- Closure tables on MySQL should now get junction columns defined the same way as the parent's primary key (typeorm issue 9600).

**How it was tested**
- `tsc --noEmit` reported no type errors.
- I ran `npm run test:ts -- test/functional/tree-tables/closure-table/closure-table-mysql.ts`. It reported 3 passing in 9ms, but that result doesn't count as verification. The `mysql` entry in `ormconfig.json` has `"skip": true`, so no connections were created. The tests loop over an empty connection list and pass without checking anything.
- To check the fix properly, set `skip` to `false` for `mysql` and point it at a running MySQL server, then rerun that file. I didn't do this because I had no MySQL server available and didn't change `ormconfig.json`.

**Side effects for reviewers**
- Existing closure tables whose parent primary key has these options will show a schema diff on the next `synchronize` or migration generation, because the junction columns will now differ from what was created before. For example, an `unsigned` parent key will make the junction columns `unsigned`.
- That diff is the intended correction, but it alters production columns, so it's worth noting in release notes.
- Parent primary columns without these options are unaffected.