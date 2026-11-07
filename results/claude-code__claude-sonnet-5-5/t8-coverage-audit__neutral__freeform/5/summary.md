I fixed five migrations that built SQL from caller input. The 9 tests pass. I read all 40 migrations, not just grepped them.

## PR description

**What changed**

These five migrations had lookup helpers that formatted caller-supplied values into the SQL string. Each now uses a bound `?` parameter:

| Migration | Helper | Was |
|---|---|---|
| 0009 | `find_account` | f-string |
| 0018 | `lookup_invoice` | `%` formatting |
| 0031 | `accounts_named` | `+` concatenation |
| 0037 | `payments_by_method` | `.format` |
| 0039 | `notes_matching` | f-string inside a `LIKE` |

For 0039 the pattern is now `'%' || ? || '%'` with `term` bound.

The other 35 migrations are fine. They use only constant DDL or constant SQL, or already bind their values. That includes the literal `LIKE` patterns in 0027, 0028 and 0033, which take no input. I also grepped `ledgerly/` and `scripts/` for the same pattern and found nothing.

**Testing**

- `pytest` gives 9 passed.
- `tests/test_injection.py` already covers 0009, 0018 and 0031 with the payload `x' OR '1'='1`.
- I added no tests for 0037 and 0039. Their helpers are fixed the same way, but nothing exercises them with a hostile value.

**Side effects for the reviewer**

- These migrations are already numbered and may already be applied. I edited them in place and did not add new ones, so there is no renumbering and the history stays append-only. The `upgrade()` results are unchanged, because the only values passed in are constants from each module.
- In 0039, `%` and `_` inside `term` still act as `LIKE` wildcards, as they did before. The values are fixed constants (`obsolete`, `superseded`), so this has no effect today. It would matter only if a caller passed untrusted text, and escaping would be needed then.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>