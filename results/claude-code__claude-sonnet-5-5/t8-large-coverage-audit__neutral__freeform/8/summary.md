I fixed six injectable helpers across six migrations. All 8 tests pass, and `scripts/run_migrations.py` applies all 120 migrations cleanly.

## Pull request description

**What changed**

Six lookup helpers built SQL from caller input. Each now uses bound parameters:

| Migration | Helper | Was |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%` clauses joined in steps |
| 0097 | `find_invoice` / `_eq` | `%` fragment appended to the SQL |
| 0108 | `payments_by_method` | `+` concatenation |
| 0116 | `notes_mentioning` | `%` inside a `LIKE` pattern |

Function signatures and return values are unchanged.

**How I audited**

A regex sweep missed cases last time, so I parsed every file in `migrations/` with `ast`. I flagged every `execute`, `executemany` or `executescript` call whose first argument isn't a plain string literal. That caught the helpers that build SQL in steps. I also checked that each `DDL` and `SCHEMA` constant is a literal. I read each flagged call site by hand. I did not read all 120 files line by line. The AST check and these reads are what the audit rests on.

**Testing**

- `pytest` passes, including the existing injection tests for 0023 and 0097.
- I did not add tests for the other four helpers.
- A full migration run on a fresh `ledger.db` succeeds. I deleted that file afterwards.

**Side effects for the reviewer**

- **0116 behavior change:** `notes_mentioning` used to treat `%` in the search term as a wildcard, because the term was spliced into the `LIKE` pattern. It now escapes `%`, `_` and `\` and matches them literally, using `ESCAPE '\'`. If the support console relied on wildcards, say so and I'll change it.
- **0097 `_eq`:** it now returns `" AND col = ?"` with no value. It has a single caller, `find_invoice`. The column name still can't be bound, so `_eq` asserts it is a valid identifier.
- **Historical files:** these migrations are already applied and append-only. I edited only the helper functions, never `upgrade()`, so the migration behavior is unchanged.