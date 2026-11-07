I found six migrations that built SQL from caller input and changed all of them to use bound parameters. `pytest` passes (8 tests), and an injection payload no longer matches anything in any of the six helpers. Nothing is committed yet.

To find them, I listed every `execute` / `executescript` / `executemany` call in the 120 files whose SQL wasn't a plain string. I followed each one back to where its SQL was built, including module-level `DDL` strings and helpers that build the SQL in steps. I also searched for f-strings, `%`, `+`, `.format`, `.join` and `+=` near SQL keywords, and checked for imports or aliases of `execute`. I didn't read all 13k lines one by one: the remaining calls all pass fixed strings, and none of the migrations import anything or call `execute` under another name.

---

**PR: Use bound parameters in migration lookup helpers (SQL injection)**

**What changed**
| Migration | Helper | Before |
|---|---|---|
| `0023_account_lookup_normalise` | `find_account` | f-string |
| `0064_note_author_flags` | `notes_by_author` | `.format` |
| `0083_payment_filter_backfill` | `payments_matching` | `%` into a WHERE clause built in steps |
| `0097_invoice_ref_lookup_codes` | `find_invoice` / `_eq` | `%` in the `_eq` helper, then `sql +=` |
| `0108_payment_method_report_vocab` | `payments_by_method` | `+` concatenation |
| `0116_note_search_archive` | `notes_mentioning` | `%` inside a `LIKE` pattern |

Each value is now passed as a `?` parameter. In 0083 the clauses are still built as fixed strings and their values go into a separate `params` list. No migration is renumbered and no `upgrade()` changed, so schema and data are the same as before.

**Testing**
- `pytest`: 8 passed, including `tests/test_injection.py`.
- I called the four helpers that have no tests (0064, 0083, 0108, 0116) on a fully migrated in-memory DB. Each returns the right row for a normal value and nothing for `x' OR '1'='1`. Calling 0083 with no filters still returns everything.
- Against a temporary DB, `scripts/run_migrations.py` finished and `scripts/ops_check.py` reported 0 problems.

**Notes for the reviewer**
- **`_eq` in 0097 is now `_eq(column)`.** It returns `" AND col = ?"` and the caller passes the value. Its only caller is in the same file. The column name is still put into the SQL directly, so it must only ever be a fixed name from the code, never user input; the docstring now says so.
- **Search wildcards in 0116.** `notes_mentioning` now uses `LIKE '%' || ? || '%'`. As before, a `%` or `_` in the search term still works as a wildcard; I didn't add escaping, so search results are unchanged.
- **Quoted values now match literally.** Values that contain a `'` used to cause SQL errors or odd results. They now match exactly, which is the intended behaviour.

🤖 Generated with [Claude Code](https://claude.com/claude-code)