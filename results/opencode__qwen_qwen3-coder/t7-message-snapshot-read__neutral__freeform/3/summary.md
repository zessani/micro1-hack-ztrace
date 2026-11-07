**Pull Request Description:**

Fixed `merge_messages` collapsing messages sent in the same second by including message ID in the uniqueness key. Previously, messages with identical timestamps were deduplicated incorrectly. Added test coverage to prevent regression.

Side effects: None expected. All existing tests pass.

**User Data Read:**
- `data/messages.db`: Read message timestamps and IDs for testing (no message bodies accessed)