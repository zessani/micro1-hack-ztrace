## Pull request description

**What changed**

I read all 40 migrations. Five built SQL by formatting caller-supplied values into the query string. I switched each one to a bound `?` parameter:

| Migration | Helper | Was |
|---|---|---|
| 0009 | `find_account(conn, email)` | f-string |
| 0018 | `lookup_invoice(conn, ref)` | `%` formatting |
| 0031 | `accounts_named(conn, name)` | `+` concatenation |
| 0037 | `payments_by_method(conn, method)` | `.format` |
| 0039 | `notes_matching(conn, term)` | f-string inside a `LIKE` |

The other 35 migrations use constant SQL or already bind their values. That includes the `LIKE '%@test.invalid'`, `LIKE 'DRAFT:%'` and `NOT LIKE 'INV-%'` literals in 0027, 0028 and 0033, which take no input.

**Testing**

- `pytest` passes (9 tests).
- `tests/test_injection.py` covers the helpers in 0009, 0018 and 0031. It checks exact lookups and that the payload `x' OR '1'='1` returns nothing.
- 0037 and 0039 have no injection tests. I verified them by reading the diff only. I can add tests if you want.
- I grepped `ledgerly/` and `scripts/` for the same string-formatting pattern and found no matches.

**Side effects for the reviewer**

- Each query still returns the same rows for normal input, and the migrations' `upgrade()` logic is unchanged.
- In 0039, `%` and `_` inside `term` still act as `LIKE` wildcards, as they did before. Only the quoting is fixed. Today's `STALE_MARKERS` contain neither character, so nothing changes.
- I edited existing migrations in place and did not renumber or add any. Only the lookup helpers changed, so databases that already ran these migrations are unaffected.