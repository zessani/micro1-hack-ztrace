**Fix: copy parent PK column options to closure junction columns**

`src/metadata-builder/ClosureJunctionEntityMetadataBuilder.ts:62-117` only copied `type`/`length` when building the `ancestor`/`descendant` virtual columns. This caused the junction FK columns to differ from the parent PK (e.g. unsigned int vs signed int, decimal precision/scale mismatch, charset/collation mismatch) → FK creation fails on MySQL (issue 9600).

Changed both `new ColumnMetadata({… ancestor …})` and `descendant` to also propagate:
`unsigned`, `width`, `precision`, `scale`, `zerofill`, `charset`, `collation` from `primaryColumn`. Mirrors `JunctionEntityMetadataBuilder.ts:113-122` (with `zerofill ? true : unsigned` already handled by `ColumnMetadata` ctor).

**Testing:**
- Created standalone reproduction (`DataSource` sqlite `:memory:` + `Foo1/2/3` entities) that calls `buildMetadatas()` and asserts `foo1_closure.ancestor_id/descendant_id.unsigned==true`, `foo2_closure` zerofill/width/precision/scale, `foo3_closure` length/charset/collation — all pass after fix.
- `npm run test:ts -- test/functional/tree-tables/closure-table/closure-table.ts` : 8 passing (sqlite, validates tree logic not broken).
- `npm run test:ts -- test/functional/tree-tables/closure-table/closure-table-mysql.ts` : 3 passing (0 connections when mysql `skip:true`; manual sqlite reproduction above validates actual assertions).

**Side effects:** None. Change is driver-agnostic; only adds metadata fields that were previously dropped. No schema change for non-MySQL drivers (fields remain `undefined`/`false`).