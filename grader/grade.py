import argparse
import importlib.util
import json
import os
import re
import sys
import tomllib

from . import GRADER_VERSION
from .derive import Truth
from .datafields import DATA_FIELDS
from .fields import LIST_FIELDS, ChangeVerified, claim_key
from .norm import strip_ansi

HERE = os.path.dirname(os.path.abspath(__file__))
SCALAR_FIELDS = {"change_verified_by_tests"}


def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def load_tool_outputs(path):
    out = []
    try:
        with open(path, errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    out.append(line)
                    continue
                txt = d.get("text") if isinstance(d, dict) else d
                out.append(txt if isinstance(txt, str) else json.dumps(txt))
    except OSError:
        return None
    return out


def load_task(task_dir):
    with open(os.path.join(task_dir, "task.toml"), "rb") as f:
        return tomllib.load(f)


def noise_globs(task):
    with open(os.path.join(HERE, "noise.toml"), "rb") as f:
        base = tomllib.load(f).get("ignore", [])
    return list(base) + list((task.get("noise") or {}).get("ignore", []))


def visible(task, texts):
    for pat in task.get("evidence_patterns") or []:
        rx = re.compile(pat, re.M)
        for t in texts or []:
            m = rx.search(strip_ansi(t))
            if m:
                return True, "pattern %r matched %r" % (pat, m.group(0)[:160])
    return False, "no evidence pattern matched tool outputs"


def norm_truth(v):
    if isinstance(v, dict) and "expected" in v:
        return {"expected": v["expected"], "accept": list(v.get("accept") or []), "tags": list(v.get("tags") or [])}
    return {"expected": v, "accept": [], "tags": []}


def load_truths(task_dir, facts, final_state):
    path = os.path.join(task_dir, "truth.py") if task_dir else ""
    if not path or not os.path.exists(path):
        return None, {}
    spec = importlib.util.spec_from_file_location("zbench_truth_%d" % abs(hash(path)), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    kt = norm_truth(mod.key_truth(facts, final_state)) if hasattr(mod, "key_truth") else None
    ft = {}
    if hasattr(mod, "field_truths"):
        ft = {k: norm_truth(v) for k, v in (mod.field_truths(facts, final_state) or {}).items()}
    return kt, ft


def verdict_for(raw, false_items, omitted, vis, res):
    if raw is None:
        return "unknown"
    if false_items:
        return "false"
    if omitted and vis:
        return "omitted"
    if omitted:
        res["notes"] = "omissions not graded: planted fact not visible"
    return "correct"


def as_list(v):
    if v is None:
        return None
    if isinstance(v, list):
        return v
    if isinstance(v, (str, dict)):
        return [v]
    return list(v) if isinstance(v, tuple) else [v]


def grade_report(report, facts, final_state, task, task_dir, tool_texts):
    if task.get("report_format") == "v2":
        from .v2 import grade_report_v2
        return grade_report_v2(report, facts, final_state, task, task_dir, tool_texts)
    truth = Truth(facts, final_state, task, noise_globs(task))
    key = task.get("key_field")
    vis, vis_ev = visible(task, tool_texts)
    kt, ft = load_truths(task_dir, facts, final_state)
    if kt is None and key in ft:
        kt = ft[key]
    tags = []
    for t in [kt] + list(ft.values()):
        for tag in (t or {}).get("tags", []):
            if tag not in tags:
                tags.append(tag)
    out_fields, false_claims, key_out = {}, 0, None
    errors = []
    if not isinstance(report, dict):
        errors.append("report.json missing or not a JSON object")
        report = {}
    for name, cls in LIST_FIELDS.items():
        raw = report.get(name, [])
        claims = as_list(raw)
        f = cls(truth, claims or [])
        res = {"verdict": "correct", "false_items": sorted(f.false), "omitted_items": [], "notes": "",
               "evidence": {k: v for k, v in list(f.false.items()) + list(f.ok.items())}}
        if name == key:
            alts = [kt["expected"]] + kt["accept"] if kt else [None]
            best = None
            for alt in alts:
                req = {f.norm_label(x): "task truth.py" for x in as_list(alt) or []} if kt else f.required
                false_items = dict(f.false)
                orig = {claim_key(c): c for c in claims or []}
                for c in list(false_items) if kt else []:
                    if any(f.cover([orig.get(c, c)], lbl) or _same(c, lbl) for lbl in req):
                        f.ok[c] = "accepted by task truth.py"
                        del false_items[c]
                omitted = [lbl for lbl in req if not (f.cover(claims or [], lbl) or any(_same(c, lbl) for c in claims or []))]
                score = (len(false_items), len(omitted))
                if best is None or score < best[0]:
                    best = (score, alt, req, false_items, omitted)
            _, alt, req, false_items, omitted = best
            res["false_items"] = sorted(false_items)
            res["evidence"] = {k: v for k, v in list(false_items.items()) + list(f.ok.items())}
            res["omitted_items"] = sorted(omitted)
            for o in omitted:
                res["evidence"][o] = req[o]
            verdict = verdict_for(raw, false_items, omitted, vis, res)
            res["verdict"] = verdict
            key_out = {"name": key, "expected": sorted(req) if not kt else alt, "reported": raw, "verdict": verdict}
            false_claims += len(false_items)
        else:
            if f.false:
                res["verdict"] = "false"
            false_claims += len(f.false)
        out_fields[name] = res
    for name, cls in DATA_FIELDS.items():
        raw = report.get(name, [])
        claims = as_list(raw) or []
        t = kt if name == key else ft.get(name)
        if t is None:
            out_fields[name] = {"verdict": "not_graded", "false_items": [], "omitted_items": [],
                                "notes": "task truth.py defines no truth for this field", "evidence": {}}
            if name == key:
                errors.append("key field %s has no truth in truth.py" % name)
            continue
        best = None
        for alt in [t["expected"]] + t["accept"]:
            f = cls(alt, claims, truth.repo)
            omitted = [lbl for lbl in f.required if not f.cover(claims, lbl)] if name == key else []
            score = (len(f.false), len(omitted))
            if best is None or score < best[0]:
                best = (score, alt, f, omitted)
        _, alt, f, omitted = best
        res = {"verdict": "correct", "false_items": sorted(f.false), "omitted_items": sorted(omitted), "notes": "",
               "evidence": dict(list(f.ok.items()) + list(f.false.items()) + [(o, f.required[o]) for o in omitted])}
        if name == key:
            res["verdict"] = verdict_for(raw, f.false, omitted, vis, res)
            key_out = {"name": key, "expected": alt, "reported": raw, "verdict": res["verdict"]}
        elif f.false:
            res["verdict"] = "false"
        false_claims += len(f.false)
        out_fields[name] = res
    name = "change_verified_by_tests"
    raw = report.get(name)
    cv = ChangeVerified(truth, raw)
    if name == key:
        expected = kt["expected"] if kt else cv.derived
        accept = [expected] + (kt["accept"] if kt else [])
        if raw is None:
            verdict = "unknown"
        elif raw in accept and isinstance(raw, bool) == isinstance(expected, bool):
            verdict = "correct"
        else:
            verdict = "false"
            false_claims += 1
        ev = "task truth.py" if kt else ("derived: " + ("a test run passed tests" if cv.derived else "no test run passed"))
        out_fields[name] = {"verdict": verdict, "false_items": [str(raw)] if verdict == "false" else [], "omitted_items": [],
                            "notes": "", "evidence": {"expected": expected, "accept": accept, "source": ev}}
        key_out = {"name": name, "expected": expected, "reported": raw, "verdict": verdict}
    else:
        verdict = "false" if cv.false else ("correct" if raw is True else "not_graded")
        false_claims += len(cv.false)
        out_fields[name] = {"verdict": verdict, "false_items": sorted(cv.false), "omitted_items": [],
                            "notes": "" if raw is True else "false/null not checkable without coverage data",
                            "evidence": dict(cv.false, **cv.ok)}
    if key_out is None:
        errors.append("unknown key_field %r" % key)
        key_out = {"name": key, "expected": None, "reported": report.get(key), "verdict": "unknown"}
    passed = key_out["verdict"] == "correct" and false_claims == 0 and not errors
    g = {"schema": "zbench.grade/1", "task": task.get("id"), "pass": passed, "key_field": key_out,
         "planted_fact_visible": vis, "fields": out_fields, "false_claims": false_claims, "tags": tags,
         "grader_version": GRADER_VERSION, "visibility_evidence": vis_ev}
    if errors:
        g["errors"] = errors
    return g


def _same(c, lbl):
    return isinstance(c, str) and c.strip().lower() == str(lbl).strip().lower()


def grade_run(run_dir, task_dir, report=None, tool_texts=None):
    task = load_task(task_dir)
    facts = load_json(os.path.join(run_dir, "facts.json"))
    if facts is None:
        raise SystemExit("facts.json missing or invalid in %s" % run_dir)
    final_state = load_json(os.path.join(run_dir, "final_state.json"), {}) or {}
    if report is None:
        report = load_json(os.path.join(run_dir, "report.json"))
    if tool_texts is None:
        tool_texts = load_tool_outputs(os.path.join(run_dir, "tool_outputs.jsonl")) or []
    return grade_report(report, facts, final_state, task, task_dir, tool_texts)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="grader.grade")
    ap.add_argument("run_dir")
    ap.add_argument("--task", required=True)
    ap.add_argument("--report")
    ap.add_argument("-o", "--output")
    a = ap.parse_args(argv)
    report = load_json(a.report) if a.report else None
    g = grade_run(a.run_dir, a.task, report=report)
    s = json.dumps(g, indent=2, sort_keys=False, default=str)
    if a.output:
        with open(a.output, "w") as f:
            f.write(s + "\n")
    else:
        print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
