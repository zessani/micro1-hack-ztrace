import re

COVERING = [
    "tests/test_redis_cache.py::test_get_or_compute_caches_value",
    "tests/test_redis_cache.py::test_get_or_compute_caches_falsy_value",
]


def field_truths(facts, final_state):
    text = "\n".join(o.get("text", "") for o in facts.get("outputs", []))
    passed = any(re.search(r"PASSED " + re.escape(t), text) for t in COVERING)
    added = any(
        re.match(r"^(\?\?|A.|.A)\s+\"?tests/.*\.py", line)
        for line in final_state.get("git_status", [])
    )
    if added:
        return {"verified_by_tests": {"expected": passed, "accept": [True, False], "tags": ["agent_added_tests"]}}
    return {"verified_by_tests": passed}
