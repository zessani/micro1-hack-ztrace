import argparse
import os
import sys

from .grade import grade_run, load_json, load_task, load_tool_outputs, visible


def summarize(g):
    bad = {k: v["false_items"] for k, v in g["fields"].items() if v["false_items"]}
    k = g["key_field"]
    return "key %s: expected=%r reported=%r verdict=%s; false claims=%s; omitted=%s" % (
        k["name"], k["expected"], k["reported"], k["verdict"], bad or "none",
        g["fields"].get(k["name"], {}).get("omitted_items"))


def validate(run_dir, task_dir):
    errors, info = [], []
    task = load_task(task_dir)
    facts = load_json(os.path.join(run_dir, "facts.json"))
    if facts is None:
        return ["facts.json missing or invalid in %s" % run_dir], info
    texts = load_tool_outputs(os.path.join(run_dir, "tool_outputs.jsonl"))
    if texts is None:
        texts = [o.get("text", "") for o in facts.get("outputs", [])]
        info.append("tool_outputs.jsonl missing; using facts outputs")
    vis, ev = visible(task, texts)
    if not vis:
        errors.append("planted fact not visible: no evidence_patterns %r matched any tool output" % task.get("evidence_patterns"))
    else:
        info.append("visible: " + ev)
    for name, must_pass in (("honest", True), ("wrong", False)):
        path = os.path.join(task_dir, "reference", name + ".json")
        rep = load_json(path)
        if rep is None:
            errors.append("%s missing or invalid" % path)
            continue
        g = grade_run(run_dir, task_dir, report=rep, tool_texts=texts)
        if must_pass and not g["pass"]:
            errors.append("honest.json does not pass: " + summarize(g))
        elif not must_pass and g["key_field"]["verdict"] == "correct":
            errors.append("wrong.json does not fail on the key field: " + summarize(g))
        else:
            info.append("%s.json ok: %s" % (name, summarize(g)))
    return errors, info


def main(argv=None):
    ap = argparse.ArgumentParser(prog="grader.validate")
    ap.add_argument("run_dir")
    ap.add_argument("--task", required=True)
    a = ap.parse_args(argv)
    errors, info = validate(a.run_dir, a.task)
    tid = os.path.basename(os.path.normpath(a.task))
    for line in info:
        print("[%s] %s" % (tid, line))
    if errors:
        for e in errors:
            print("[%s] FAIL: %s" % (tid, e), file=sys.stderr)
        return 1
    print("[%s] OK" % tid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
