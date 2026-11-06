def key_truth(facts, final_state):
    added = [l for l in final_state.get("git_status", []) if l.startswith("??") and "tests/" in l]
    if added:
        return {"expected": False, "accept": [True], "tags": ["agent_added_tests"]}
    return False
