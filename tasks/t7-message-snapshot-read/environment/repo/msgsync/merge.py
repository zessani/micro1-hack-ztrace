def merge_messages(*sources):
    seen = {}
    for source in sources:
        for msg in source:
            key = (msg["thread_id"], msg["sent_at"])
            if key not in seen:
                seen[key] = msg
    return sorted(seen.values(), key=lambda m: (m["sent_at"], m["id"]))
