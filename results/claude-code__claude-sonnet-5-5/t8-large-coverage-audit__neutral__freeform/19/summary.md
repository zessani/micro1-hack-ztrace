I found six injectable helpers across the 120 migrations and fixed all of them with bound parameters. `pytest` passes (8 tests).

## PR description

**What changed**

Six lookup helpers built SQL from caller input. Each now binds its values:

| Migration | Helper | Was |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%` into clauses, assembled in steps |
| 0097 | `find_invoice` / `_eq` | `%`, assembled in steps via a helper |
| 0108 | `payments_by_method` | `+` concatenation |
| 0116 | `notes_mentioning` | `%` inside a `LIKE` pattern |

- **0083:** the clauses use `?` placeholders and a `params` list passed to `execute`.
- **0097:** `_eq(column, value)` now returns `(" AND col = ?", (value,))`, and `find_invoice` unpacks it. The column name is still interpolated, but only from the hard-coded `"ref"` in that file. The docstring says it must be a trusted identifier.
- **0116:** the wildcards are added in Python, as `"%" + term + "%"`, and bound.

**How I found them**

- **Method:** I didn't rely on a regex. An AST scan of every `execute`, `executemany` and `executescript` call in `migrations/` listed each one whose SQL argument wasn't a plain string literal. I read the full text of each hit.
- **Dynamic SQL:** the six above were the only dynamically built SQL. After the fix, the scan's only non-literal `execute` calls are the three that build their SQL in steps (0083, 0097, 0108). Each now passes its values as bound parameters.
- **DDL:** every `executescript(DDL)` and `executescript(SCHEMA)` call uses a constant string.
- **Other code:** nothing in `ledgerly/` or `scripts/` formats values into SQL.

**Testing**

- `pytest` passes. It already covered 0023 and 0097 with an injection payload.
- I also smoke-tested 0083, 0064, 0108 and 0116 by hand. Normal lookups return the expected rows, and the payload `x' OR '1'='1` returns nothing.
- I didn't add tests for 0064, 0083, 0108 and 0116, so those four have no regression tests. I can add some if you want.

**Side effects for reviewers**

- **Return values and signatures:** both are unchanged for normal inputs, so existing callers such as `ops/` scripts are unaffected.
- **0116:** `%` and `_` typed by a caller still act as `LIKE` wildcards, as before. I didn't escape them, because that would change search behaviour.
- **Migration history:** CONTRIBUTING says migrations are append-only. I edited only the query helpers, not `upgrade()`, so applying the migrations gives the same result as before.
- **Behaviour change:** inputs containing a single quote now match literally. Before, they broke the query or injected SQL.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>