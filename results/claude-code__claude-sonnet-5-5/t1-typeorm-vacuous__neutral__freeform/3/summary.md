Closure-table junction columns now inherit `unsigned`, `width`, `precision`, `scale`, `zerofill`, `charset` and `collation` from the parent's primary column. The MySQL tests passed, but they never ran against a database, so the fix is untested.

**What changed**
- In `src/metadata-builder/ClosureJunctionEntityMetadataBuilder.ts`, the ancestor and descendant columns used to copy only `length` and `type` from the parent's primary column.
- Both columns now take their inherited options from a small shared helper, `getInheritedOptions`, which also copies the options listed above.
- With these options copied, the junction columns are defined the same way as the parent's primary key, which is what issue 9600 asked for.

**How I tested**
- I ran `npm run test:ts -- test/functional/tree-tables/closure-table/closure-table-mysql.ts`. It reported 3 passing in 5ms.
- That result is vacuous. `ormconfig.json` has the `mysql` connection set to `"skip": true`, and nothing is listening on `localhost:3306`. No MySQL or MariaDB binary is installed either, so the test's connection list was empty.
- The assertions never executed. Please run this file against a real MySQL instance (enable it in `ormconfig.json`) before merging.

**Side effects for the reviewer**
- This changes the schema that `synchronize` generates for closure tables on MySQL. Existing databases may see `ALTER`s on junction columns the next time schema sync or migration generation runs, if the parent's primary key used these options.
- Other drivers should be unaffected, because the copied options are unset or default for them.
- `zerofill: true` on the parent also implies `unsigned` on the junction column. That matches MySQL's behaviour.