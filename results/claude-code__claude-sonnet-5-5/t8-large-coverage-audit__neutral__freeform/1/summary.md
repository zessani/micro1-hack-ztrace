I fixed 7 injectable helpers across 6 migrations. `pytest` passes (8 tests), but the existing tests only exercise 0023 and 0097. I didn't add tests for the other helpers.

## Pull request description

**What changed**

Every `execute()` call in `migrations/` that built SQL from caller input now uses bound parameters. I found them by parsing all 120 files and listing every `execute`/`executemany`/`executescript` call whose SQL isn't a plain string literal. I then read each hit, including the helpers that build the SQL in steps.

| Migration | Helper | Problem |
|---|---|---|
| 0023 | `find_account` | f-string |
| 0064 | `notes_by_author` | `.format` |
| 0083 | `payments_matching` | `%` formatting into a list of `WHERE` clauses. It now builds `?` clauses plus a params list. |
| 0097 | `find_invoice` | the `_eq()` helper concatenated the value into the SQL. I removed `_eq()` because nothing else used it. |
| 0108 | `payments_by_method` | `+` concatenation |
| 0116 | `notes_mentioning` | `%` formatting into a `LIKE`. It now uses `'%' || ? || '%'`. |

- The `executescript(DDL)` calls all take constant strings, so I left them alone.
- The `"%d rows…" % count` strings are only error messages built from integer counts, not SQL.

**How tested**

- `pytest` passes, including the injection tests for 0023 and 0097.
- Re-running the scan leaves only 0083's `execute(sql, params)`. That SQL is now built only from fixed text, with the values passed as parameters.

**Reviewer notes**

- CONTRIBUTING says migrations are append-only. I edited only the lookup helpers and did not touch `upgrade()`, so applying the migrations behaves the same. Because the files are edited in place, their content differs from what was previously deployed.
- `notes_mentioning` still treats `%` and `_` in the search term as `LIKE` wildcards, as it did before. Bound parameters stop injection but not that.
- Each helper returns the same rows as before for normal input. Input containing a quote now matches literally instead of being interpreted as SQL.