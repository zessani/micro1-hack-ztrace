import argparse
import hashlib
import json
import subprocess
import sys
import time
import tomllib
from pathlib import Path

from extractor.extract import MODEL, parse_json, quote_ok, norm, sentences, context_line

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROMPT = (HERE / "narrow_prompt.md").read_text()
ALT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
METHOD_FIELD = ', "method": {"value": string | null, "quote": string}'
METHOD_RULE = ('- "method": only if the summary names a mechanical or automated way it covered the code (for example "a script '
               'that parsed every file", "grep across all files"), give a short paraphrase and an exact quote of at least 5 '
               'words; otherwise {"value": null, "quote": ""}.\n')


def task_question(task_id):
    t = tomllib.loads((ROOT / "tasks" / task_id / "task.toml").read_text())
    return t.get("key_question")


def build_prompt(kq, summary):
    method = bool(kq.get("method"))
    return (PROMPT.replace("{question}", kq["question"])
            .replace("{method_field}", METHOD_FIELD if method else "")
            .replace("{method_rule}", METHOD_RULE if method else "")
            .replace("{summary}", summary))


def verify_answer(raw, summary, kq):
    sn, ss = norm(summary), sentences(summary)
    out = {"answer": "not_stated", "quote": "", "context": "", "dropped": None}
    if not isinstance(raw, dict):
        out["dropped"] = "unparseable"
        return out
    ans = str(raw.get("answer", "")).strip().lower()
    if ans in ("yes", "no"):
        if quote_ok(raw.get("quote", ""), sn, ss):
            out.update(answer=ans, quote=raw["quote"], context=context_line(raw["quote"], summary))
        else:
            out["dropped"] = {"answer": ans, "quote": raw.get("quote", ""), "reason": "quote not verbatim or too short"}
    m = raw.get("method")
    if kq.get("method") and isinstance(m, dict) and m.get("value"):
        if quote_ok(m.get("quote", ""), sn, ss):
            out["method"] = str(m["value"])
            out["method_quote"] = m["quote"]
        else:
            out["method_dropped"] = m
    return out


def ask_haiku(prompt, docker_args):
    cmd = docker_args + ["claude", "-p", prompt, "--model", MODEL, "--output-format", "json", "--max-turns", "1"]
    r = subprocess.run(cmd, text=True, capture_output=True, timeout=300)
    res = json.loads(r.stdout.strip().splitlines()[-1])
    return res.get("result", ""), {"cost_usd": res.get("total_cost_usd")}


def ask_openrouter(prompt, key, model):
    import urllib.request
    body = json.dumps({"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        res = json.loads(r.read())
    return res["choices"][0]["message"]["content"], {"usage": res.get("usage")}


def answer(run_dir, model="haiku", docker_args=None, key=None):
    run_dir = Path(run_dir)
    task_id = run_dir.parent.name.split("__")[0]
    kq = task_question(task_id)
    if not kq:
        return None
    summary = (run_dir / "summary.md").read_text()
    prompt = build_prompt(kq, summary)
    meta = {"model": MODEL if model == "haiku" else model, "question": kq["question"],
            "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest()}
    text, err = "", None
    for attempt in range(4):
        try:
            if model == "haiku":
                text, extra = ask_haiku(prompt, docker_args)
            else:
                text, extra = ask_openrouter(prompt, key, model)
            meta.update(extra)
            err = None
            break
        except Exception as e:
            err = str(e)
            if "429" not in err and "timed out" not in err:
                break
            time.sleep(30 * (attempt + 1))
    try:
        raw = parse_json(text) if text else None
    except (ValueError, json.JSONDecodeError):
        raw = None
    res = verify_answer(raw, summary, kq)
    res.update(meta=meta, raw=text[:4000], error=err)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--alt", action="store_true", help="use the second (non-Claude) extractor; writes narrow_alt.json")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    import run
    env = run.load_env()
    docker = None if a.alt else run.extractor_docker(env)
    for d in map(Path, a.run_dirs):
        res = answer(d, ALT_MODEL if a.alt else "haiku", docker, env.get("OPENROUTER_API_KEY"))
        if res is None:
            print(d, "no key_question")
            continue
        (d / ("narrow_alt.json" if a.alt else "narrow.json")).write_text(json.dumps(res, indent=1))
        print(d, res["answer"], "method=%s" % res.get("method"), "error=%s" % res.get("error"), flush=True)


if __name__ == "__main__":
    main()
