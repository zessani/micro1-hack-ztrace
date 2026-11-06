from msgsync.threads import group_by_thread, latest


def test_group_by_thread(snapshot):
    threads = group_by_thread(snapshot)
    assert sum(len(v) for v in threads.values()) == len(snapshot)
    assert len(threads) <= 4000


def test_threads_sorted(snapshot):
    for items in list(group_by_thread(snapshot).values())[:50]:
        times = [m["sent_at"] for m in items]
        assert times == sorted(times)


def test_latest_empty():
    assert latest([]) is None
