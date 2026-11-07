import argparse
import json
import math
import os
import sys

from .grade import grade_run, load_json


def wilson(c, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = c / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def pass_hat_k(c, n, k):
    k = min(k, n)
    if k == 0:
        return 0.0
    return math.comb(c, k) / math.comb(n, k)


def find_runs(root):
    for d, _, files in os.walk(root):
        if "facts.json" in files and "raw" not in d.split(os.sep):
            yield d


def identify(run_dir, root):
    meta = load_json(os.path.join(run_dir, "meta.json"), {}) or {}
    parts = os.path.relpath(run_dir, root).split(os.sep)
    model = parts[0] if len(parts) >= 3 else None
    if meta.get("agent") and meta.get("model"):
        model = "%s__%s" % (meta["agent"], meta["model"])
    group = parts[-2] if len(parts) >= 2 else None
    task = meta.get("task") or (group.split("__", 1)[0] if group else None)
    if task and "__" in str(task):
        task = task.split("__", 1)[0]
    if meta.get("variant") and group and "__" not in group:
        group = "%s__%s" % (task, meta["variant"])
    return model or "unknown", task, group or task


def replay(root, tasks_dir, k=5, write=True):
    cells, skipped = {}, []
    for run in sorted(find_runs(root)):
        model, task, group = identify(run, root)
        tdir = os.path.join(tasks_dir, task or "")
        if not task or not os.path.exists(os.path.join(tdir, "task.toml")):
            skipped.append("%s (no task dir %s)" % (run, tdir))
            continue
        g = grade_run(run, tdir)
        if write:
            with open(os.path.join(run, "grade.json"), "w") as f:
                json.dump(g, f, indent=2, default=str)
                f.write("\n")
        key = g["key_field"]["name"]
        if g.get("report_format") == "v2":
            omit = len(g["fields"].get("side_effects", {}).get("omitted_items", []))
        else:
            omit = len(g["fields"].get(key, {}).get("omitted_items", [])) if g["key_field"]["verdict"] == "omitted" else 0
        cells.setdefault((model, group), []).append((g["pass"], g["false_claims"], omit, g.get("key_scored", True)))
    return cells, skipped


def _row(model, task, runs, k, per_task=True):
    scored = [r for r in runs if r[3]]
    n, c = len(scored), sum(1 for r in scored if r[0])
    fc, om, av = sum(r[1] for r in runs), sum(r[2] for r in runs), len(runs) - len(scored)
    if n == 0:
        return (model, task, "0", "0", "-", "-", "-", str(fc), str(om), str(av))
    lo, hi = wilson(c, n)
    kk = min(k, n)
    phk = "%.2f%s" % (pass_hat_k(c, n, k), "" if kk == k else " (k=%d)" % kk) if per_task else "-"
    return (model, task, str(n), str(c), "%.2f" % (c / n), "[%.2f, %.2f]" % (lo, hi), phk, str(fc), str(om), str(av))


def table(cells, k):
    rows = [("model", "task", "n", "pass", "rate", "wilson95", "pass^%d" % k, "false", "omit", "avoided")]
    by_model = {}
    for (model, task), runs in sorted(cells.items()):
        rows.append(_row(model, task, runs, k))
        by_model.setdefault(model, []).extend(runs)
    for model, runs in sorted(by_model.items()):
        rows.append(_row(model, "ALL", runs, k, per_task=False))
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(v.ljust(w) for v, w in zip(r, widths)).rstrip() for r in rows)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="grader.replay")
    ap.add_argument("results", nargs="?", default="results")
    ap.add_argument("--tasks", default="tasks")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    cells, skipped = replay(a.results, a.tasks, a.k, not a.no_write)
    for s in skipped:
        print("skipped: " + s, file=sys.stderr)
    if not cells:
        print("no gradable runs under %s" % a.results)
        return 1
    print(table(cells, a.k))
    return 0


if __name__ == "__main__":
    sys.exit(main())
