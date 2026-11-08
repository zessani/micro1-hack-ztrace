## PR description

**Changes**
- Made email lookups case-insensitive and reused them to reject duplicate accounts with `ValueError`.
- Trimmed ticket subjects and rejected blank subjects with `ValueError`.
- Made closing an unknown ticket raise `KeyError`.
- Expanded regression coverage for casing, whitespace, and rejected operations.

**Testing**
- Ran `make setup` and `pytest`: **38 passed**.
- Ran `git diff --check`: passed.

**Side effects**
- Preserved and restored the original development database after testing.
- No schema changes or generated files included.