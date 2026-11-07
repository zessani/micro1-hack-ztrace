import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "claude-haiku-5-5"
PROMPT = (HERE / "prompt.md").read_text()
MIN_WORDS = 5
COUNTS = ("passed", "failed", "skipped", "reruns")
QUOTE_CHARS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def build_prompt(summary):
    return PROMPT.replace("{summary}", summary)


def norm(text):
    t = (text or "").translate(QUOTE_CHARS).lower()
    t = re.sub(r"[`*_#>]", "", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip(" .,;:!?\"'()-")


def sentences(summary):
    parts = re.split(r"(?<=[.!?])\s+|\n+", (summary or "").translate(QUOTE_CHARS))
    return {norm(p) for p in parts if norm(p)}


def quote_ok(quote, summary_norm, summary_sentences):
    q = norm(quote)
    if not q or q not in summary_norm:
        return False
    return len(q.split()) >= MIN_WORDS or q in summary_sentences


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def context_line(quote, summary):
    q = norm(quote)
    for line in (summary or "").translate(QUOTE_CHARS).splitlines():
        if q and q in norm(line):
            return line.strip()
    return quote or ""


def verify(raw, summary):
    sn, ss = norm(summary), sentences(summary)
    dropped = []

    def keep(field, item):
        if isinstance(item, dict) and quote_ok(item.get("quote", ""), sn, ss):
            return True
        dropped.append({"field": field, "claim": item})
        return False

    def boolean(field, obj):
        if not isinstance(obj, dict) or obj.get("value") is None:
            return None
        return obj["value"] if keep(field, obj) else None

    rep = {"changes": [], "testing": [], "verified_by_tests": None, "side_effects": [], "operations": [],
           "review": None, "summary": raw.get("summary") or ""}
    for c in raw.get("changes") or []:
        if keep("changes", c) and c.get("path"):
            rep["changes"].append(c["path"])
    for t in raw.get("testing") or []:
        if keep("testing", t):
            e = {"command": t.get("command") or "", "outcome": t.get("outcome") or "passed",
                 "context": context_line(t.get("quote", ""), summary)}
            qn = norm(t.get("quote", ""))
            nums = set(re.findall(r"\d[\d,]*", qn))
            nums |= {n.replace(",", "") for n in nums}
            if re.search(r"\b(no|none|zero)\b", qn):
                nums.add("0")
            for k in COUNTS:
                if isinstance(t.get(k), int) and not isinstance(t.get(k), bool) and str(t[k]) in nums:
                    e[k] = t[k]
            if not e["command"] and not any(t.get(k) for k in COUNTS):
                for k in COUNTS:
                    e.pop(k, None)
            rep["testing"].append(e)
    rep["verified_by_tests"] = boolean("verified_by_tests", raw.get("verified_by_tests"))
    for s in raw.get("side_effects") or []:
        if re.match(r"\s*(none|no |nothing|n/a|did not|didn't|not )", norm(s.get("detail", "")) or ""):
            dropped.append({"field": "side_effects", "claim": s, "reason": "negated"})
            continue
        if keep("side_effects", s):
            rep["side_effects"].append({"type": s.get("type") or "other", "detail": s.get("detail") or "",
                                        "quote": s.get("quote") or "", "context": context_line(s.get("quote", ""), summary)})
    for o in raw.get("operations") or []:
        if keep("operations", o):
            rep["operations"].append({"name": o.get("name") or "", "outcome": o.get("outcome") or "complete",
                                      "detail": o.get("detail") or ""})
    rv = raw.get("review")
    if isinstance(rv, dict):
        r = {"complete": boolean("review.complete", rv.get("complete")),
             "all_fixed": boolean("review.all_fixed", rv.get("all_fixed"))}
        m = rv.get("method")
        if isinstance(m, dict) and m.get("value") and keep("review.method", m):
            r["method"] = str(m["value"])
            r["method_quote"] = m.get("quote", "")
        rep["review"] = r if any(r.get(k) is not None for k in ("complete", "all_fixed", "method")) else None
    return rep, dropped


def extract(summary, docker_args):
    prompt = build_prompt(summary)
    cmd = docker_args + ["claude", "-p", prompt, "--model", MODEL, "--output-format", "json", "--max-turns", "1"]
    r = subprocess.run(cmd, text=True, capture_output=True, timeout=300)
    meta = {"model": MODEL, "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(),
            "min_quote_words": MIN_WORDS, "exit_code": r.returncode}
    try:
        res = json.loads(r.stdout.strip().splitlines()[-1])
        meta.update({"cost_usd": res.get("total_cost_usd"), "raw": res.get("result", "")})
        rep, dropped = verify(parse_json(res.get("result", "")), summary)
        meta["dropped"] = dropped
        meta["dropped_count"] = len(dropped)
        return rep, meta
    except (json.JSONDecodeError, IndexError, ValueError, AttributeError) as e:
        meta.update({"error": str(e), "raw": r.stdout[-4000:], "stderr": r.stderr[-2000:]})
        return None, meta


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--rerun", action="store_true")
    a = ap.parse_args(argv)
    if not a.rerun:
        print(build_prompt((Path(a.run_dirs[0]) / "summary.md").read_text()))
        return
    sys.path.insert(0, str(HERE.parent))
    import run
    docker = run.extractor_docker(run.load_env())
    for d in map(Path, a.run_dirs):
        rep, meta = extract((d / "summary.md").read_text(), docker)
        (d / "extractor.json").write_text(json.dumps(meta, indent=1))
        if rep is not None:
            (d / "report.json").write_text(json.dumps(rep, indent=1))
        print(d, "dropped", meta.get("dropped_count"), "error", meta.get("error"))


if __name__ == "__main__":
    main()


ALT_MODEL = "google/gemini-omni-1.2-flash"


def extract_openrouter(summary, api_key, model=ALT_MODEL):
    import urllib.request
    body = json.dumps({"model": model, "temperature": 0,
                       "messages": [{"role": "user", "content": build_prompt(summary)}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    meta = {"model": model, "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(), "min_quote_words": MIN_WORDS}
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read())
        text = res["choices"][0]["message"]["content"]
        meta.update({"raw": text, "usage": res.get("usage")})
        rep, dropped = verify(parse_json(text), summary)
        meta.update({"dropped": dropped, "dropped_count": len(dropped)})
        return rep, meta
    except Exception as e:
        meta["error"] = str(e)
        return None, meta
