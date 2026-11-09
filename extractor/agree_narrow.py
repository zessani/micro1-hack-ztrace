import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from extractor.agree import main_runs, sample  # noqa: E402
from grader.narrow import grade_multi, grade_narrow  # noqa: E402
from grader.grade import load_task  # noqa: E402


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def compare(runs):
    ans, ver, skipped = [], [], 0
    for d in runs:
        p, q = d / "narrow.json", d / "narrow_alt.json"
        if not (p.exists() and q.exists() and (d / "grade.json").exists()):
            skipped += 1
            continue
        a, b = json.loads(p.read_text()), json.loads(q.read_text())
        if b.get("error") and (b.get("answer") == "not_stated" or not b.get("questions")) and not b.get("raw"):
            skipped += 1
            continue
        g = json.loads((d / "grade.json").read_text())
        base = dict(g, key_field=g.get("secondary", {}).get("key_field", g["key_field"]))
        task = load_task(str(ROOT / "tasks" / d.parent.name.split("__")[0]))
        sc = "method_disclosed" in g.get("tags", []) or None
        va = g.get("narrow", {}).get("verdict") or grade_narrow(base, task, a, sc)["verdict"]
        if task.get("key_questions"):
            texts = [json.loads(l).get("text", "") for l in open(d / "tool_outputs.jsonl")] if (d / "tool_outputs.jsonl").exists() else []
            vb = grade_multi(base, task, b, True, texts)["verdict"]
            qa = {q.get("id"): q.get("answer") for q in a.get("questions", [])}
            for q in b.get("questions", []):
                ans.append((qa.get(q.get("id")), q.get("answer")))
        else:
            vb = grade_narrow(base, task, b, True)["verdict"]
            ans.append((a["answer"], b["answer"]))
        ver.append(("pass" if va in ("correct", "not_scored") else "fail", "pass" if vb in ("correct", "not_scored") else "fail"))
    return {"n": len(ans), "skipped_alt_unavailable": skipped,
            "answer_agreement": "%d/%d" % (sum(x == y for x, y in ans), len(ans)), "answer_kappa": kappa(ans),
            "pass_fail_agreement": "%d/%d" % (sum(x == y for x, y in ver), len(ver)), "pass_fail_kappa": kappa(ver)}


def main():
    results = ROOT / "results"
    runs = main_runs(results)
    fixed = json.loads((results / "_agreement" / "agreement.json").read_text())["rows"]
    picked = [results / r["run"] for r in fixed]
    allff = sorted(d for d in results.glob("*__*/*__freeform/[0-9]*") if (ROOT / "tasks" / d.parent.name.split("__")[0]).is_dir())
    out = {"primary": "claude-haiku-5-5", "alt": "nvidia/nemotron-3-ultra-550b-a55b (free endpoint for the first 35 answers, paid endpoint for the rest; same model)",
           "note": "aggregate only; per-run comparison withheld until the hand check is complete",
           "handcheck_sample_20": compare(picked), "all_freeform_runs": compare(allff)}
    (results / "_agreement" / "narrow_agreement.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
