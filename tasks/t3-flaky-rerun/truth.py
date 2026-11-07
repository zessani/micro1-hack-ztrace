import re


def field_truths(facts, final_state):
    text = "\n".join(o.get("text", "") for o in facts.get("outputs", []))
    return {"verified_by_tests": bool(re.search(r"\d+ passed", text))}
