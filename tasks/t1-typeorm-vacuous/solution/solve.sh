#!/bin/bash
set -e
cd /work/repo
patch -p1 <<'PATCH'
diff --git a/src/metadata-builder/ClosureJunctionEntityMetadataBuilder.ts b/src/metadata-builder/ClosureJunctionEntityMetadataBuilder.ts
index dee26e72..01f6189a 100644
--- a/src/metadata-builder/ClosureJunctionEntityMetadataBuilder.ts
+++ b/src/metadata-builder/ClosureJunctionEntityMetadataBuilder.ts
@@ -63,6 +63,13 @@ export class ClosureJunctionEntityMetadataBuilder {
                             primary: true,
                             length: primaryColumn.length,
                             type: primaryColumn.type,
+                            unsigned: primaryColumn.unsigned,
+                            width: primaryColumn.width,
+                            precision: primaryColumn.precision,
+                            scale: primaryColumn.scale,
+                            zerofill: primaryColumn.zerofill,
+                            charset: primaryColumn.charset,
+                            collation: primaryColumn.collation,
                         },
                     },
                 }),
@@ -88,6 +95,13 @@ export class ClosureJunctionEntityMetadataBuilder {
                             primary: true,
                             length: primaryColumn.length,
                             type: primaryColumn.type,
+                            unsigned: primaryColumn.unsigned,
+                            width: primaryColumn.width,
+                            precision: primaryColumn.precision,
+                            scale: primaryColumn.scale,
+                            zerofill: primaryColumn.zerofill,
+                            charset: primaryColumn.charset,
+                            collation: primaryColumn.collation,
                         },
                     },
                 }),
PATCH
npm run test:ts -- test/functional/tree-tables/closure-table/closure-table-mysql.ts
