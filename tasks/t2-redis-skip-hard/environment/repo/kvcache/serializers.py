"""Value (de)serialization for the Redis cache."""
import json


def dumps(value):
    return json.dumps(value, sort_keys=True)


def loads(raw):
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)
