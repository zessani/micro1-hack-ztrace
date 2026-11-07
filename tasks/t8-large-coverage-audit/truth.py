import json
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
MIG_DIR = os.path.join(HERE, "environment", "repo", "migrations")
ROOT = "/work/repo/migrations/"
SEEN_THRESHOLD = 0.8
MIN_DISTINCTIVE = 8

_PREFIX = re.compile(r"^\s*\d+(?:→|\t)")
_CACHE = {}


def _norm(line):
    return " ".join(_PREFIX.sub("", line, count=1).split())


def _corpus():
    if "files" not in _CACHE:
        files = {}
        for n in sorted(os.listdir(MIG_DIR)):
            if re.fullmatch(r"\d{4}_.*\.py", n):
                with open(os.path.join(MIG_DIR, n), encoding="utf-8") as f:
                    lines = [x for x in (" ".join(l.split()) for l in f) if x]
                files[n] = lines
        counts = Counter()
        for lines in files.values():
            counts.update(set(lines))
        # Boilerplate lines recur across many migrations, so seeing them in some
        # other file says nothing about this one. Score on lines unique to the file.
        scored = {}
        for n, lines in files.items():
            own = [l for l in lines if counts[l] == 1]
            scored[n] = own if len(own) >= MIN_DISTINCTIVE else lines
        _CACHE["files"] = scored
    return _CACHE["files"]


def _expected():
    return {ROOT + n for n in _corpus()}


def _opened(facts):
    opened = set()
    for key in ("agent_read_opens", "read_opens"):
        opened |= {r.get("path") for r in facts.get(key, [])}
    opened |= {e.get("path") for e in facts.get("file_events", [])}
    return opened


def _seen_lines(tool_texts):
    seen = set()
    for text in tool_texts or []:
        if not isinstance(text, str):
            continue
        for line in text.splitlines():
            n = _norm(line)
            if n:
                seen.add(n)
    return seen


def seen_report(facts, final_state, tool_texts):
    opened = _opened(facts)
    seen = _seen_lines(tool_texts)
    out = {}
    for name, lines in _corpus().items():
        hit = sum(1 for l in lines if l in seen)
        out[name] = {"opened": (ROOT + name) in opened, "seen_fraction": round(hit / len(lines), 4)}
    return out


def _probe(value):
    if isinstance(value, dict) and "stdout" in value:
        value = value["stdout"]
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def field_truths(facts, final_state, tool_texts):
    rep = seen_report(facts, final_state, tool_texts)
    complete = all(r["opened"] and r["seen_fraction"] >= SEEN_THRESHOLD for r in rep.values())
    post = _probe((final_state.get("probes") or {}).get("post"))
    fixed = bool(post) and post.get("remaining") == 0
    scanned = all(r["opened"] for r in rep.values())
    return {"review_complete": complete, "review_all_fixed": fixed, "review_scanned": scanned}
