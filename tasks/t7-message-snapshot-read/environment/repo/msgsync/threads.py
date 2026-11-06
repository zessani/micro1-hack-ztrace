from collections import defaultdict


def group_by_thread(messages):
    threads = defaultdict(list)
    for msg in messages:
        threads[msg["thread_id"]].append(msg)
    for items in threads.values():
        items.sort(key=lambda m: (m["sent_at"], m["id"]))
    return dict(threads)


def latest(messages):
    return max(messages, key=lambda m: (m["sent_at"], m["id"]), default=None)
