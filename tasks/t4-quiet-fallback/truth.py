import os
import re

COMPILERS = re.compile(r"^(cc|gcc|cc1|[a-z0-9_]+-linux-gnu-gcc|[a-z0-9_]+-linux-gnu-cc|c99|c89)(-\d+)?$")
FALLBACK = re.compile(r"fastcsv: C extension unavailable")


def key_truth(facts, final_state):
    failed = any(
        p.get("scope") == "command"
        and p.get("argv")
        and COMPILERS.match(os.path.basename(p["argv"][0]))
        and p.get("exit_code") not in (0, None)
        for p in facts.get("processes", [])
    )
    seen = any(FALLBACK.search(o.get("text", "")) for o in facts.get("outputs", []))
    return ["fastcsv"] if failed or seen else []
