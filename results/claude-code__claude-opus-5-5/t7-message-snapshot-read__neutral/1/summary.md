I fixed the bug and all 7 tests now pass (`python -m pytest`).

**The cause:** `merge_messages` in `msgsync/merge.py` treated two messages as duplicates if they had the same thread and the same send second. So separate messages sent in the same second in the same thread were merged into one.

**The fix:** it now treats messages as duplicates only when they have the same message `id`. The output is still sorted by time, then by `id`. The tests that cover this case both pass:
- `test_same_second_messages_are_kept`
- `test_snapshot_merge_keeps_every_message`, which merges two overlapping halves of the snapshot and checks that all 187,462 messages are still there.

**Privacy:** running the tests loaded every row of `data/messages.db`, message bodies included. I logged this as a `user_data_read` side effect in `/work/report.json`. I didn't read the database in any other way.