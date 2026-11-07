import argparse
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from extractor.extract import extract_openrouter  # noqa: E402
from grader.grade import grade_run  # noqa: E402

ALT = "nvidia/nemotron-3-ultra-550b-a55b:free"
MAIN_MODELS = ("claude-code__claude-opus-5-5", "claude-code__claude-sonnet-5-5",
               "opencode__meta_muse-spark-open", "opencode__qwen_qwen3-coder")


def main_runs(results):
    runs = []
    for m in MAIN_MODELS:
        for d in sorted((results / m).glob("*__neutral__freeform/[0-9]*")):
            task = d.parent.name.split("__")[0]
            if (d / "grade.json").exists() and (d / "summary.md").exists() and (ROOT / "tasks" / task).is_dir():
                runs.append(d)
    return runs


def sample(runs, n, seed):
    rng = random.Random(seed)
    strata = defaultdict(list)
    for d in runs:
        strata[(d.parent.parent.name, d.parent.name)].append(d)
    keys = sorted(strata)
    rng.shuffle(keys)
    picked = []
    while len(picked) < n and any(strata.values()):
        for k in keys:
            if strata[k] and len(picked) < n:
                picked.append(strata[k].pop(rng.randrange(len(strata[k]))))
    failing = [d for d in runs if d not in picked and not json.loads((d / "grade.json").read_text())["pass"]]
    return sorted(picked, key=str), failing


def fields(rep):
    rep = rep or {}
    rv = rep.get("review") or {}
    return {
        "verified_by_tests": rep.get("verified_by_tests"),
        "side_effect_types": sorted({s.get("type") for s in rep.get("side_effects") or []}),
        "operations": sorted((o.get("name", "")[:30], o.get("outcome")) for o in rep.get("operations") or []),
        "review_complete": rv.get("complete"),
        "review_method": bool(rv.get("method")),
        "testing_runs": len(rep.get("testing") or []),
    }


def verdicts(g):
    return {"pass": g["pass"], "key": g["key_field"]["verdict"], "false_claims": g["false_claims"],
            "omissions": g.get("omissions", 0)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20261108)
    ap.add_argument("--model", default=ALT)
    a = ap.parse_args(argv)
    import run
    key = run.load_env()["OPENROUTER_API_KEY"]
    results = Path(a.results)
    picked, _ = sample(main_runs(results), a.n, a.seed)
    out_dir = results / "_agreement"
    out_dir.mkdir(exist_ok=True)
    rows, sheet = [], ["# Hand-check sheet", "",
                       "For each run, read the summary and the evidence, then fill in `your verdict` (pass / false claim / omission) and a note.",
                       "Sample: %d main-matrix free-form runs, stratified by model and task, seed %d." % (len(picked), a.seed), ""]
    for d in picked:
        rel = str(d.relative_to(results))
        summary = (d / "summary.md").read_text()
        haiku = json.loads((d / "report.json").read_text()) if (d / "report.json").exists() else None
        for attempt in range(4):
            alt, meta = extract_openrouter(summary, key, a.model)
            if alt is not None or "429" not in str(meta.get("error")):
                break
            time.sleep(30 * (attempt + 1))
        g_haiku = json.loads((d / "grade.json").read_text())
        g_alt = grade_run(str(d), str(ROOT / "tasks" / d.parent.name.split("__")[0]), report=alt) if alt else None
        fh, fa = fields(haiku), fields(alt) if alt else None
        vh, va = verdicts(g_haiku), verdicts(g_alt) if g_alt else None
        rows.append({"run": rel, "alt_error": meta.get("error"), "alt_dropped": meta.get("dropped_count"),
                     "fields_haiku": fh, "fields_alt": fa, "verdict_haiku": vh, "verdict_alt": va,
                     "field_agree": {k: fa is not None and fh[k] == fa[k] for k in fh},
                     "verdict_agree": {k: va is not None and vh[k] == va[k] for k in vh}})
        parts = "; ".join("%s=%s" % (p["name"], p["verdict"]) for p in g_haiku["key_field"].get("parts", []))
        control = json.loads((d / "control.json").read_text()) if (d / "control.json").exists() else {}
        sheet += ["## %s" % rel, "",
                  "- grader: pass=%s, key: %s, false claims=%s, omissions=%s, tags=%s" % (
                      g_haiku["pass"], parts, g_haiku["false_claims"], g_haiku.get("omissions", 0), g_haiku.get("tags")),
                  "- false-claim categories: %s" % (g_haiku.get("false_claim_categories") or "none"),
                  "- control: %s → %s" % (control.get("question", ""), (control.get("answer") or "")[:400].replace("\n", " ")),
                  "- your verdict: ", "- note: ", "", "<details><summary>agent summary</summary>", "", "```", summary[:6000],
                  "```", "</details>", ""]
        print(rel, "alt_error=%s" % meta.get("error"), "verdict_agree=%s" % rows[-1]["verdict_agree"], flush=True)
    keys_f = list(rows[0]["field_agree"]) if rows else []
    keys_v = list(rows[0]["verdict_agree"]) if rows else []
    ok = [r for r in rows if r["fields_alt"] is not None]
    summary = {"alt_model": a.model, "primary_model": "claude-haiku-5-5", "n": len(rows), "n_alt_ok": len(ok),
               "field_agreement": {k: "%d/%d" % (sum(r["field_agree"][k] for r in ok), len(ok)) for k in keys_f},
               "verdict_agreement": {k: "%d/%d" % (sum(r["verdict_agree"][k] for r in ok), len(ok)) for k in keys_v},
               "disagreements": [r for r in rows if not all(r["verdict_agree"].values())]}
    (out_dir / "agreement.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1, sort_keys=True))
    (out_dir / "handcheck.md").write_text("\n".join(sheet))
    print(json.dumps({k: v for k, v in summary.items() if k != "disagreements"}, indent=1))


if __name__ == "__main__":
    main()
