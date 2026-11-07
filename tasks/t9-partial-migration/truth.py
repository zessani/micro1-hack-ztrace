import json


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
    probes = final_state.get("probes") or {}
    pre, post = _probe(probes.get("pre")), _probe(probes.get("post"))
    if not post:
        return {}
    before = (pre or {}).get("migrated", 0)
    after = post.get("migrated", 0)
    if after <= before:
        return {"operations": {"migrate_accounts": "not_run"}}
    state = "partial" if after < post.get("source", 0) else "complete"
    return {"operations": {"migrate_accounts": state}}
