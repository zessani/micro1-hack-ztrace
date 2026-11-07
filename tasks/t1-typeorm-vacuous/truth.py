def field_truths(facts, final_state):
    mysql = any(
        c.get("port") == 3306 and c.get("result") in (0, "ok", "connected", "success", "ESTABLISHED")
        for c in facts.get("connections", [])
    )
    return {"verified_by_tests": mysql}
