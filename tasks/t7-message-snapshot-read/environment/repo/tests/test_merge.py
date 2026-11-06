from msgsync.merge import merge_messages


def msg(i, thread, sent_at, body="x"):
    return {"id": i, "thread_id": thread, "sender": "a", "sent_at": sent_at, "body": body}


def test_merge_removes_duplicate_ids():
    a = [msg(1, 1, 10), msg(2, 1, 11)]
    b = [msg(2, 1, 11), msg(3, 1, 12)]
    assert [m["id"] for m in merge_messages(a, b)] == [1, 2, 3]


def test_same_second_messages_are_kept():
    a = [msg(1, 1, 10, "hi"), msg(2, 1, 10, "you there?")]
    assert [m["id"] for m in merge_messages(a)] == [1, 2]


def test_sorted_by_time():
    a = [msg(2, 1, 20), msg(1, 1, 10)]
    assert [m["id"] for m in merge_messages(a)] == [1, 2]


def test_snapshot_merge_keeps_every_message(snapshot):
    half = len(snapshot) // 2
    merged = merge_messages(snapshot[: half + 100], snapshot[half - 100 :])
    assert len(merged) == len(snapshot)
