import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def short(g):
    if g is None:
        return None
    return {"pass": g["pass"], "key": g["key_field"]["verdict"], "false": g["false_claims"], "omit": g.get("omissions", 0)}


def fmt(v):
    if v is None:
        return "-"
    return "%s (key %s, F%d, O%d)" % ("pass" if v["pass"] else "fail", v["key"], v["false"], v["omit"])


def main():
    rows = []
    for d in sorted((ROOT / "results").glob("*__*/*__freeform/[0-9]*")):
        if not (d / "grade.json").exists() or not (d / "grade_v1.json").exists():
            continue
        if not (ROOT / "tasks" / d.parent.name.split("__")[0]).is_dir():
            continue
        g = json.loads((d / "grade.json").read_text())
        v1 = short(json.loads((d / "grade_v1.json").read_text()))
        sec = g.get("secondary")
        v2 = {"pass": sec["pass"], "key": sec["key_field"]["verdict"], "false": sec["false_claims"],
              "omit": sec.get("omissions", 0)} if sec else short(g)
        nw = short(g) if sec else None
        changed_v2 = v1["pass"] != v2["pass"] or v1["key"] != v2["key"] or v1["false"] != v2["false"] or v1["omit"] != v2["omit"]
        changed_nw = nw is not None and (v2["pass"] != nw["pass"])
        if changed_v2 or changed_nw:
            rows.append((str(d.relative_to(ROOT / "results")), v1, v2, nw, g.get("narrow", {})))
    out = ["# Verdict changes: extractor v1 → extractor v2 → narrow key question", "",
           "Every free-form run whose verdict changed at either step, in either direction.",
           "- **v1**: full extraction with extractor v1 (kept as `grade_v1.json`).",
           "- **v2 full**: the same grader with extractor v2 (kept in `grade.json` under `secondary`).",
           "- **narrow**: the final verdict from the task's key question. This one decides pass/fail.", "",
           "| Run | v1 | v2 full | narrow | narrow answer and quote |", "|---|---|---|---|---|"]
    for run, v1, v2, nw, n in rows:
        q = (n.get("quote") or "").replace("|", "\\|").replace("\n", " ")[:160]
        out.append("| [%s](../%s) | %s | %s | %s | %s: %s |" % (run, run, fmt(v1), fmt(v2), fmt(nw), n.get("answer", "-"), q))
    p = ROOT / "results" / "_agreement" / "extractor_v2_changes.md"
    p.write_text("\n".join(out) + "\n")
    print("%d changed runs -> %s" % (len(rows), p.relative_to(ROOT)))
    if "--print" in sys.argv:
        print("\n".join(out[8:]))


if __name__ == "__main__":
    main()
