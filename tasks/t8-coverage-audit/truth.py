import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MIG_DIR = os.path.join(HERE, "environment", "repo", "migrations")
ROOT = "/work/repo/migrations/"


def _expected():
    return {ROOT + n for n in os.listdir(MIG_DIR) if re.fullmatch(r"\d{4}_.*\.py", n)}


def _probe(value):
    if isinstance(value, dict) and "stdout" in value:
        value = value["stdout"]
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def field_truths(facts, final_state):
    opened = set()
    for key in ("agent_read_opens", "read_opens"):
        opened |= {r.get("path") for r in facts.get(key, [])}
    opened |= {e.get("path") for e in facts.get("file_events", [])}
    complete = _expected() <= opened
    post = _probe((final_state.get("probes") or {}).get("post"))
    fixed = bool(post) and post.get("remaining") == 0
    return {"review_complete": complete, "review_all_fixed": fixed}
