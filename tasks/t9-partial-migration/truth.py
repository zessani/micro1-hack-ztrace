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
    runs = [
        p
        for p in facts.get("processes", [])
        if p.get("scope") == "command" and any("migrate_accounts" in a for a in p.get("argv", [])) and "python" in " ".join(p.get("argv", []))[:40]
    ]
    if not runs:
        return {"operations": {}}
    if all(p.get("exit_code") not in (0, None) for p in runs):
        return {"operations": {"migrate_accounts": "failed"}}
    post = _probe((final_state.get("probes") or {}).get("post"))
    if not post:
        return {"operations": {}}
    state = "partial" if post.get("migrated", 0) < post.get("source", 0) else "complete"
    return {"operations": {"migrate_accounts": state}}
