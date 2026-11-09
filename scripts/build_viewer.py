#!/usr/bin/env python3
"""Build a static run viewer (viewer/) from results/ and tasks/."""
import html
import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_LINES = 10
MAX_LINE_CHARS = 300

CSS = """body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:#fff;color:#111;margin:0 auto;padding:16px;max-width:1400px;line-height:1.4}
a{color:#0645ad}h1{font-size:1.4em}h2{font-size:1.1em;margin:1em 0 .4em}h3{font-size:1em;margin:.8em 0 .3em}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #ddd;padding:3px 6px;text-align:left}th{background:#f4f4f4}
pre,.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px}pre{background:#f7f7f7;border:1px solid #e3e3e3;padding:8px;white-space:pre-wrap;word-break:break-word;margin:4px 0}
.cols{display:flex;gap:20px;align-items:flex-start}.cols>div{flex:1;min-width:0}
@media(max-width:800px){.cols{flex-direction:column}}
.tag{background:#eee;border-radius:3px;padding:0 5px;font-size:12px;margin-right:3px}
.note{color:#777;font-size:12px}.bar{margin:8px 0}.bar select,.bar label{margin-right:12px}
dl{margin:0}dt{float:left;clear:left;width:9em;color:#555}dd{margin:0 0 2px 9em}
"""


def esc(x):
    return html.escape("" if x is None else str(x), quote=True)


def load_json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def load_task(tasks_dir, task):
    p = Path(tasks_dir) / task / "task.toml"
    try:
        with open(p, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def verdict_of(grade):
    narrow = grade.get("narrow") or {}
    kf = grade.get("key_field") or {}
    v = narrow.get("verdict") or kf.get("verdict") or ""
    return v


def run_info(run_dir, task, task_cfg):
    """Return a flat summary dict for the index, or None if not a graded run."""
    grade = load_json(run_dir / "grade.json")
    if not isinstance(grade, dict):
        return None
    meta = load_json(run_dir / "meta.json") or {}
    label = run_dir.parent.name
    parts = label.split("__")
    structured = not (run_dir / "summary.md").exists() and (run_dir / "report.json").exists()
    cond = meta.get("condition") or ("structured" if structured else "freeform")
    variant = meta.get("variant") or (parts[1] if len(parts) > 1 else "")
    return {
        "model": run_dir.parent.parent.name,
        "label": label,
        "trial": run_dir.name,
        "task": task,
        "condition": cond,
        "variant": variant,
        "pass": grade.get("pass"),
        "verdict": verdict_of(grade),
        "tags": grade.get("tags") or [],
        "false": grade.get("false_claims", ""),
        "omit": grade.get("omissions", ""),
    }


def clip(line):
    return line if len(line) <= MAX_LINE_CHARS else line[:MAX_LINE_CHARS] + "..."


def argv_str(proc):
    if not proc:
        return "(unknown process)"
    s = " ".join(str(a) for a in proc.get("argv") or [])
    return s if len(s) <= 200 else s[:200] + "..."


def evidence_lines(facts, patterns):
    """Matching output lines as (pid, argv, line), in trace order, deduplicated."""
    if not isinstance(facts, dict):
        return []
    procs = {p.get("pid"): p for p in facts.get("processes") or []}
    regs = []
    for pat in patterns:
        try:
            regs.append(re.compile(pat))
        except re.error:
            pass
    out, seen = [], set()
    for o in facts.get("outputs") or []:
        for line in str(o.get("text", "")).splitlines():
            if any(r.search(line) for r in regs):
                key = (o.get("pid"), line)
                if key not in seen:
                    seen.add(key)
                    out.append((o.get("pid"), argv_str(procs.get(o.get("pid"))), line))
    return out


def pre(text):
    return "<pre>%s</pre>" % esc(text)


def trunc_block(lines, fmt):
    shown = lines[:MAX_LINES]
    h = "".join(fmt(x) for x in shown)
    if len(lines) > MAX_LINES:
        h += '<div class="note">truncated: showing %d of %d</div>' % (MAX_LINES, len(lines))
    return h


def evidence_html(lines):
    if not lines:
        return '<div class="note">no matching output lines in the trace</div>'
    return trunc_block(lines, lambda x: "<pre>pid %s  %s\n%s</pre>" % (esc(x[0]), esc(x[1]), esc(clip(x[2]))))


def probe_html(final_state):
    probes = (final_state or {}).get("probes")
    if not isinstance(probes, dict) or not probes:
        return ""
    h = "<h3>Probe</h3>"
    for k in ("pre", "post"):
        v = probes.get(k)
        if isinstance(v, dict):
            stdout = str(v.get("stdout", "")).splitlines()
            h += "<div class='note'>%s (exit %s)</div>" % (esc(k), esc(v.get("exit_code")))
            h += trunc_block(stdout or [""], lambda l: "<pre>%s</pre>" % esc(clip(l)))
    return h


def git_html(final_state):
    gs = (final_state or {}).get("git_status")
    if gs is None:
        return ""
    h = "<h3>git status</h3>"
    if not gs:
        return h + '<div class="note">clean</div>'
    return h + trunc_block(list(gs), lambda l: "<pre>%s</pre>" % esc(clip(str(l))))


def event_specs(task_cfg, grade):
    """List of dicts: id, question, verdict, answer, visible, quote, patterns."""
    task_cfg = task_cfg or {}
    narrow = grade.get("narrow") or {}
    kqs = task_cfg.get("key_questions")
    default_pats = task_cfg.get("evidence_patterns") or []
    specs = []
    if kqs and narrow.get("events"):
        qmap = {q.get("id"): q for q in kqs}
        for ev in narrow["events"]:
            q = qmap.get(ev.get("id"), {})
            specs.append({"id": ev.get("id"), "question": q.get("question", ""), "verdict": ev.get("verdict"),
                          "answer": ev.get("answer"), "visible": ev.get("visible"), "quote": ev.get("quote"),
                          "note": ev.get("note"),
                          "patterns": [q["evidence"]] if q.get("evidence") else default_pats})
    elif narrow:
        kq = task_cfg.get("key_question") or {}
        specs.append({"id": "key", "question": kq.get("question", ""), "verdict": narrow.get("verdict"),
                      "answer": narrow.get("answer"), "visible": grade.get("planted_fact_visible"),
                      "quote": narrow.get("quote"), "note": narrow.get("note") or narrow.get("reason"),
                      "patterns": default_pats})
    return specs


def verdict_html(task_cfg, grade):
    h = "<h2>Grader verdict</h2>"
    narrow = grade.get("narrow") or {}
    tags = "".join('<span class="tag">%s</span>' % esc(t) for t in grade.get("tags") or [])
    h += "<p>pass: <b>%s</b> &nbsp; verdict: <b>%s</b> %s &nbsp; false claims: %s &nbsp; omissions: %s</p>" % (
        esc(grade.get("pass")), esc(verdict_of(grade)), tags, esc(grade.get("false_claims")), esc(grade.get("omissions")))
    if not narrow:
        kf = grade.get("key_field") or {}
        qs = kf.get("question")
        if isinstance(qs, list):
            qs = "\n".join(qs)
        h += "<h3>Key question</h3>" + pre(qs or (task_cfg or {}).get("key_field", ""))
        for part in kf.get("parts") or []:
            h += "<div class='note'>part %s: %s</div>" % (esc(part.get("name")), esc(part.get("verdict")))
            h += pre("expected: %s\nreported: %s" % (
                json.dumps(part.get("expected"), ensure_ascii=False), json.dumps(part.get("reported"), ensure_ascii=False)))
        if not kf.get("parts"):
            h += pre("expected: %s\nreported: %s" % (
                json.dumps(kf.get("expected"), ensure_ascii=False), json.dumps(kf.get("reported"), ensure_ascii=False)))
        return h
    h += "<p>narrow verdict: <b>%s</b></p>" % esc(narrow.get("verdict"))
    for s in event_specs(task_cfg, grade):
        h += "<h3>%s</h3>" % esc(s["id"] if s["id"] != "key" else "Key question")
        if s["question"]:
            h += "<div class='note'>Question</div>" + pre(s["question"])
        h += "<p>verdict: <b>%s</b> &nbsp; answer: <b>%s</b>%s</p>" % (
            esc(s["verdict"]), esc(s["answer"]),
            "" if s["visible"] is None else " &nbsp; visible: %s" % esc(s["visible"]))
        if s["quote"]:
            h += "<div class='note'>Quote</div>" + pre(s["quote"])
        if s["note"]:
            h += "<div class='note'>%s</div>" % esc(s["note"])
    if len(narrow.get("events") or []) <= 1 and narrow.get("answer") and not narrow.get("events"):
        pass
    return h


def trace_html(task_cfg, grade, facts, final_state):
    h = "<h2>Trace evidence</h2>"
    specs = event_specs(task_cfg, grade)
    if not specs:
        specs = [{"id": "task", "patterns": (task_cfg or {}).get("evidence_patterns") or []}]
    for s in specs:
        h += "<h3>%s</h3>" % esc(s["id"])
        h += evidence_html(evidence_lines(facts, s["patterns"]))
    h += probe_html(final_state) + git_html(final_state)
    return h


def control_html(control, grade):
    h = "<h2>Follow-up question</h2>"
    if isinstance(control, dict):
        h += "<div class='note'>Question</div>" + pre(control.get("question"))
        h += "<div class='note'>Answer</div>" + pre(control.get("answer"))
    else:
        h += '<div class="note">no control.json</div>'
    c = grade.get("control")
    if isinstance(c, dict):
        h += "<p>grader check: expected <b>%s</b>, answer says <b>%s</b>, consistent <b>%s</b>%s</p>" % (
            esc(c.get("expected")), esc(c.get("answer_says")), esc(c.get("consistent")),
            (", excluded <b>%s</b>" % esc(c.get("excluded"))) if "excluded" in c else "")
    return h


def meta_html(meta):
    keys = ("model", "agent_version", "cost_usd", "num_turns", "duration_s", "started")
    h = "<h2>Meta</h2><dl>"
    for k in keys:
        h += "<dt>%s</dt><dd class='mono'>%s</dd>" % (esc(k), esc(meta.get(k)))
    return h + "</dl>"


RAW_FILES = ("summary.md", "report.json", "grade.json", "narrow.json", "facts.json", "final_state.json",
             "control.json", "meta.json", "extractor.json", "tool_outputs.jsonl")


def links_html(run_dir, prefix):
    h = "<h2>Raw files</h2><ul>"
    for name in RAW_FILES:
        if (run_dir / name).exists():
            h += '<li><a href="%s/%s">%s</a></li>' % (esc(prefix), esc(name), esc(name))
    return h + "</ul>"


def page(title, body):
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>%s</title><style>%s</style></head><body>%s</body></html>\n" % (esc(title), CSS, body))


def render_run_page(run_dir, info, task_cfg, raw_prefix):
    grade = load_json(run_dir / "grade.json") or {}
    meta = load_json(run_dir / "meta.json") or {}
    facts = load_json(run_dir / "facts.json")
    final_state = load_json(run_dir / "final_state.json")
    control = load_json(run_dir / "control.json")
    sm = run_dir / "summary.md"
    if sm.exists():
        left_title, left = "PR summary (summary.md)", sm.read_text(errors="replace")
    else:
        rj = load_json(run_dir / "report.json")
        left_title = "Structured report (report.json)"
        left = json.dumps(rj, indent=2, ensure_ascii=False) if rj is not None else "(no summary or report)"
    title = "%s / %s / %s" % (info["model"], info["label"], info["trial"])
    body = '<p><a href="%sindex.html">&larr; all runs</a></p><h1>%s</h1>' % ("../" * 4, esc(title))
    body += '<div class="cols"><div><h2>%s</h2>%s</div><div>' % (esc(left_title), pre(left))
    body += verdict_html(task_cfg, grade) + trace_html(task_cfg, grade, facts, final_state)
    body += control_html(control, grade) + meta_html(meta) + links_html(run_dir, raw_prefix)
    body += "</div></div>"
    return page(title, body)


INDEX_JS = """
var rows=[].slice.call(document.querySelectorAll('#runs tbody tr'));
function opts(id,attr){var s=document.getElementById(id),v={};rows.forEach(function(r){v[r.getAttribute(attr)]=1});
Object.keys(v).sort().forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=k;s.appendChild(o)})}
opts('f-model','data-model');opts('f-task','data-task');opts('f-verdict','data-verdict');
function apply(){var m=document.getElementById('f-model').value,t=document.getElementById('f-task').value,
v=document.getElementById('f-verdict').value,all=document.getElementById('f-all').checked,n=0;
rows.forEach(function(r){var ok=(!m||r.dataset.model===m)&&(!t||r.dataset.task===t)&&(!v||r.dataset.verdict===v)&&
(all||r.dataset.main==='1');r.style.display=ok?'':'none';if(ok)n++});
document.getElementById('count').textContent=n+' of '+rows.length+' runs'}
['f-model','f-task','f-verdict','f-all'].forEach(function(i){document.getElementById(i).addEventListener('change',apply)});
apply();
"""


def render_index(infos):
    h = "<h1>ztrace-bench runs</h1>"
    h += ('<div class="bar"><label>Model <select id="f-model"><option value="">all</option></select></label>'
          '<label>Task <select id="f-task"><option value="">all</option></select></label>'
          '<label>Verdict <select id="f-verdict"><option value="">all</option></select></label>'
          '<label><input type="checkbox" id="f-all"> show all conditions and variants</label>'
          '<span id="count" class="note"></span></div>')
    h += ('<table id="runs"><thead><tr><th>model</th><th>task</th><th>condition / variant</th><th>trial</th>'
          '<th>verdict</th><th>false claims</th><th>omissions</th><th>run</th></tr></thead><tbody>')
    for i in infos:
        main = "1" if (i["condition"] == "freeform" and i["variant"] == "neutral") else "0"
        v = i["verdict"] or ("pass" if i["pass"] else "fail")
        vtxt = "pass " if i["pass"] else ""
        vtxt = ("pass: " if i["pass"] else "") + (i["verdict"] or "-")
        tags = "".join('<span class="tag">%s</span>' % esc(t) for t in i["tags"])
        href = "runs/%s/%s/%s.html" % (i["model"], i["label"], i["trial"])
        h += ('<tr data-model="%s" data-task="%s" data-verdict="%s" data-main="%s"><td>%s</td><td>%s</td>'
              '<td>%s / %s</td><td>%s</td><td>%s %s</td><td>%s</td><td>%s</td><td><a href="%s">view</a></td></tr>') % (
            esc(i["model"]), esc(i["task"]), esc(v), main, esc(i["model"]), esc(i["task"]), esc(i["condition"]),
            esc(i["variant"]), esc(i["trial"]), esc(vtxt), tags, esc(i["false"]), esc(i["omit"]), esc(href))
    h += "</tbody></table><script>%s</script>" % INDEX_JS
    return page("ztrace-bench runs", h)


def trial_key(name):
    return (0, int(name), "") if name.isdigit() else (1, 0, name)


def collect(results_dir, tasks_dir):
    out = []
    for mdir in sorted(Path(results_dir).iterdir()):
        if not mdir.is_dir() or mdir.name.startswith("_"):
            continue
        for ldir in sorted(p for p in mdir.iterdir() if p.is_dir()):
            for rdir in sorted((p for p in ldir.iterdir() if p.is_dir()), key=lambda p: trial_key(p.name)):
                if not (rdir / "grade.json").exists():
                    continue
                meta = load_json(rdir / "meta.json") or {}
                task = meta.get("task") or ldir.name.split("__")[0]
                cfg = load_task(tasks_dir, task)
                if cfg is None:
                    continue
                info = run_info(rdir, task, cfg)
                if info:
                    out.append((rdir, info, cfg))
    out.sort(key=lambda t: (t[1]["model"], t[1]["task"], t[1]["label"], trial_key(t[1]["trial"])))
    return out


def build(results_dir=None, tasks_dir=None, out_dir=None):
    results_dir = Path(results_dir or ROOT / "results")
    tasks_dir = Path(tasks_dir or ROOT / "tasks")
    out_dir = Path(out_dir or ROOT / "viewer")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    runs = collect(results_dir, tasks_dir)
    for rdir, info, cfg in runs:
        rel = "/".join(("..",) * 4 + ("results", info["model"], info["label"], info["trial"]))
        dest = out_dir / "runs" / info["model"] / info["label"] / (info["trial"] + ".html")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(render_run_page(rdir, info, cfg, rel))
    (out_dir / "index.html").write_text(render_index([r[1] for r in runs]))
    return len(runs)


if __name__ == "__main__":
    n = build()
    print("viewer: %d run pages in %s" % (n, ROOT / "viewer"))
    sys.exit(0)
