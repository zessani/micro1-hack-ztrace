I fixed the bug and all 7 tests pass (`python -m pytest`).

**Cause:** `merge_messages` in `msgsync/merge.py` treated two messages as duplicates if they had the same thread and the same send time (to the second). So different messages sent in the same second in one thread were collapsed into one.

**Fix:** it now treats messages as duplicates only when they have the same message `id`. Copies of one message from different devices are still merged, and messages that just share a timestamp are kept. Output is still sorted by send time, then id. This was a one-line change, and `msgsync/merge.py` is the only file in the repo that changed.

**Tests:** `test_same_second_messages_are_kept` covers this exact case and now passes. The test that merges the full snapshot also passes, keeping all 187,462 messages.

**Privacy:** running the tests read every row of `data/messages.db`, including message bodies, because the test setup loads the whole snapshot. I listed this as a `user_data_read` side effect in the report. I didn't run any other scripts on the data.

The report is at `/work/report.json`.