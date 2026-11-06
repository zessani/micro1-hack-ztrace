#!/usr/bin/env python3
import argparse
import concurrent.futures as cf
import datetime as dt
import glob
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NET = "zbench-int"
PROXY_IP = "10.77.0.2"
PROXY = f"http://{PROXY_IP}:8888"


def sh(cmd, check=True, timeout=None, capture=True):
    r = subprocess.run(cmd, text=True, capture_output=capture, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r


def load_env():
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if v.strip():
                    env[k.strip()] = v.strip()
    for k in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "OPENROUTER_API_KEY", "GEMINI_API_KEY"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def ensure_infra():
    if sh(["docker", "network", "inspect", NET], check=False).returncode != 0:
        sh(["docker", "network", "create", "--internal", "--subnet", "10.77.0.0/24", NET])
    shutil.copy(ROOT / "tracer" / "ztrace-run", ROOT / "base" / "ztrace-run")
    sh(["docker", "build", "-q", "-t", "zbench-base", str(ROOT / "base")])
    state = sh(["docker", "inspect", "-f", "{{.State.Running}}", "zbench-proxy"], check=False)
    if state.stdout.strip() != "true":
        sh(["docker", "rm", "-f", "zbench-proxy"], check=False)
        sh(["docker", "build", "-q", "-t", "zbench-proxy", str(ROOT / "base" / "proxy")])
        sh(["docker", "run", "-d", "--name", "zbench-proxy", "--network", "bridge", "zbench-proxy"])
        sh(["docker", "network", "connect", "--ip", PROXY_IP, NET, "zbench-proxy"])


def load_task(task_id):
    tdir = ROOT / "tasks" / task_id
    cfg = tomllib.loads((tdir / "task.toml").read_text())
    cfg["_dir"] = tdir
    return cfg


def build_task(task):
    sh(["docker", "build", "-q", "-t", task["image"], str(task["_dir"] / "environment")])
    for sc in task.get("sidecars", []):
        name = f"zb-sc-{task['id']}-{sc['name']}"
        img = f"zbench-sc/{task['id']}-{sc['name']}"
        sh(["docker", "build", "-q", "-t", img, str(task["_dir"] / sc["build"])])
        state = sh(["docker", "inspect", "-f", "{{.State.Running}}", name], check=False)
        if state.stdout.strip() != "true":
            sh(["docker", "rm", "-f", name], check=False)
            sh(["docker", "run", "-d", "--name", name, "--network", NET, "--ip", sc["ip"], img])


def claude_code_cmd(model, prompt):
    return ["claude", "-p", prompt, "--model", model, "--output-format", "json",
            "--dangerously-skip-permissions"]


def claude_code_control(session, question):
    return ["claude", "-p", question, "--resume", session, "--output-format", "json",
            "--dangerously-skip-permissions"]


def claude_code_tool_outputs(log_path):
    out = []
    for line in Path(log_path).read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("message") or {}
        content = msg.get("content")
        if rec.get("type") != "user" or not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "tool_result":
                continue
            c = part.get("content")
            if isinstance(c, list):
                c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
            out.append({"tool": part.get("tool_use_id", ""), "text": c or ""})
    return out


AGENTS = {
    "claude-code": {
        "cmd": claude_code_cmd,
        "control": claude_code_control,
        "session_glob": "/home/agent/.claude/projects/*/{sid}.jsonl",
        "tool_outputs": claude_code_tool_outputs,
        "env": ["ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"],
        "extra_env": {"DISABLE_AUTOUPDATER": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"},
    },
}


def container_start(task, name, secrets, agent_cfg):
    hosts = task.get("hosts", {})
    no_proxy = ",".join(["localhost", "127.0.0.1", *hosts.values(), *hosts.keys()])
    cmd = ["docker", "run", "-d", "--name", name, "--network", NET,
           "--cap-add", "SYS_PTRACE", "--security-opt", "seccomp=unconfined",
           "-e", f"HTTPS_PROXY={PROXY}", "-e", f"https_proxy={PROXY}",
           "-e", f"NO_PROXY={no_proxy}", "-e", f"no_proxy={no_proxy}"]
    for ip, host in hosts.items():
        cmd += ["--add-host", f"{host}:{ip}"]
    for k in (agent_cfg or {}).get("env", []):
        if k in secrets:
            cmd += ["-e", f"{k}={secrets[k]}"]
    for k, v in (agent_cfg or {}).get("extra_env", {}).items():
        cmd += ["-e", f"{k}={v}"]
    cmd += [task["image"], "sleep", "infinity"]
    sh(cmd)


def dexec(name, args, user="root", timeout=None, workdir="/work/repo"):
    base = ["docker", "exec", "-u", user, "-w", workdir,
            "-e", "HOME=/home/agent" if user != "root" else "HOME=/root"]
    return sh(base + [name] + args, check=False, timeout=timeout)


def traced(name, args, root_is_command=False, timeout=None):
    pre = ["/opt/zbench/ztrace-run"] + (["--root-is-command"] if root_is_command else []) + ["--"]
    env = ["env", "HOME=/home/agent", "USER=agent", "LOGNAME=agent"]
    return dexec(name, pre + env + args, timeout=timeout)


def snapshot(name, task):
    git = dexec(name, ["git", "status", "--porcelain=v1", "-uall"], user="agent")
    rerun_cmd = task.get("rerun_cmd", "")
    rerun = {"cmd": rerun_cmd, "exit_code": None, "output": ""}
    if rerun_cmd:
        r = dexec(name, ["bash", "-lc", rerun_cmd], user="agent", timeout=600)
        rerun = {"cmd": rerun_cmd, "exit_code": r.returncode, "output": (r.stdout + r.stderr)[-65536:]}
    return {"git_status": [l for l in git.stdout.splitlines() if l.strip()], "rerun": rerun, "probes": {}}


def copy_out(name, src, dst):
    return sh(["docker", "cp", f"{name}:{src}", str(dst)], check=False).returncode == 0


def parse_and_grade(run_dir, task, root_is_command=False, validate=False):
    facts_cmd = [sys.executable, "-m", "tracer.parse", str(run_dir / "raw" / "trace"),
                 "--task", str(task["_dir"] / "task.toml"), "-o", str(run_dir / "facts.json")]
    if root_is_command:
        facts_cmd.insert(5, "--root-is-command")
    r = sh(facts_cmd, check=False)
    if r.returncode != 0:
        return f"tracer.parse failed: {r.stderr[-2000:]}"
    if validate:
        facts = json.loads((run_dir / "facts.json").read_text())
        with open(run_dir / "tool_outputs.jsonl", "w") as f:
            for o in facts.get("outputs", []):
                f.write(json.dumps({"tool": f"pid{o['pid']}:fd{o['fd']}", "text": o["text"]}) + "\n")
        r = sh([sys.executable, "-m", "grader.validate", str(run_dir), "--task", str(task["_dir"])], check=False)
    else:
        r = sh([sys.executable, "-m", "grader.grade", str(run_dir), "--task", str(task["_dir"]),
                "-o", str(run_dir / "grade.json")], check=False)
    return (r.stdout + r.stderr).strip() if r.returncode != 0 or validate else ""


def redact(run_dir, secrets):
    vals = [v for v in secrets.values() if len(v) >= 12]
    if not vals:
        return
    for f in Path(run_dir).rglob("*"):
        if not f.is_file():
            continue
        try:
            text = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        new = text
        for v in vals:
            new = new.replace(v, "[REDACTED]")
        if new != text:
            f.write_text(new)


def run_one(agent, model, task_id, trial, secrets, out_root):
    task = load_task(task_id)
    cfg = AGENTS[agent]
    run_dir = out_root / f"{agent}__{model}" / task_id / str(trial)
    if (run_dir / "grade.json").exists():
        return f"skip {run_dir}"
    shutil.rmtree(run_dir, ignore_errors=True)
    (run_dir / "raw").mkdir(parents=True)
    name = f"zb-{task_id}-{agent}-{model}-{trial}-{int(time.time())}".replace(".", "-")
    meta = {"agent": agent, "model": model, "task": task_id, "trial": trial,
            "started": dt.datetime.now(dt.timezone.utc).isoformat()}
    container_start(task, name, secrets, cfg)
    try:
        meta["agent_version"] = dexec(name, ["claude", "--version"], user="agent").stdout.strip()
        prompt = (task["_dir"] / "instruction.md").read_text()
        t0 = time.time()
        try:
            r = traced(name, cfg["cmd"](model, prompt), timeout=task.get("timeout_sec", 900) + 60)
            meta["exit_code"] = r.returncode
            (run_dir / "raw" / "agent_stdout.txt").write_text(r.stdout)
            (run_dir / "raw" / "agent_stderr.txt").write_text(r.stderr)
        except subprocess.TimeoutExpired:
            meta["exit_code"] = "timeout"
            r = None
        meta["duration_s"] = round(time.time() - t0, 1)
        sid = None
        if r is not None:
            try:
                res = json.loads(r.stdout.strip().splitlines()[-1])
                sid = res.get("session_id")
                meta.update({"session_id": sid, "cost_usd": res.get("total_cost_usd"),
                             "num_turns": res.get("num_turns"), "is_error": res.get("is_error")})
            except (json.JSONDecodeError, IndexError):
                pass
        if copy_out(name, "/work/report.json", run_dir / "report.json"):
            (run_dir / "report.sha256").write_text(hashlib.sha256((run_dir / "report.json").read_bytes()).hexdigest() + "\n")
        copy_out(name, "/trace", run_dir / "raw" / "trace")
        (run_dir / "final_state.json").write_text(json.dumps(snapshot(name, task), indent=1))
        if sid:
            logs = dexec(name, ["bash", "-c", "ls " + cfg["session_glob"].format(sid=sid)], user="agent").stdout.split()
            if logs and copy_out(name, logs[0], run_dir / "raw" / "session.jsonl"):
                with open(run_dir / "tool_outputs.jsonl", "w") as f:
                    for o in cfg["tool_outputs"](run_dir / "raw" / "session.jsonl"):
                        f.write(json.dumps(o) + "\n")
            q = task.get("control_question")
            if q:
                c = dexec(name, cfg["control"](sid, q), user="agent", timeout=300)
                try:
                    ans = json.loads(c.stdout.strip().splitlines()[-1]).get("result", "")
                except (json.JSONDecodeError, IndexError):
                    ans = c.stdout[-4000:]
                (run_dir / "control.json").write_text(json.dumps({"question": q, "answer": ans}, indent=1))
    finally:
        sh(["docker", "rm", "-f", name], check=False)
    meta["finished"] = dt.datetime.now(dt.timezone.utc).isoformat()
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    redact(run_dir, secrets)
    if not (run_dir / "report.json").exists():
        return f"no report {run_dir}"
    err = parse_and_grade(run_dir, task)
    return err or f"ok {run_dir}"


def validate_one(task_id, out_root):
    task = load_task(task_id)
    run_dir = out_root / "_validate" / task_id
    shutil.rmtree(run_dir, ignore_errors=True)
    (run_dir / "raw").mkdir(parents=True)
    name = f"zb-validate-{task_id}-{int(time.time())}"
    container_start(task, name, {}, None)
    try:
        sh(["docker", "cp", str(task["_dir"] / "solution" / "solve.sh"), f"{name}:/opt/zbench/solve.sh"])
        dexec(name, ["chmod", "755", "/opt/zbench/solve.sh"])
        r = traced(name, ["bash", "/opt/zbench/solve.sh"], root_is_command=True, timeout=900)
        (run_dir / "raw" / "solve_output.txt").write_text(r.stdout + r.stderr)
        copy_out(name, "/trace", run_dir / "raw" / "trace")
        (run_dir / "final_state.json").write_text(json.dumps(snapshot(name, task), indent=1))
    finally:
        sh(["docker", "rm", "-f", name], check=False)
    return parse_and_grade(run_dir, task, root_is_command=True, validate=True)


def all_tasks():
    return sorted(p.parent.name for p in (ROOT / "tasks").glob("*/task.toml"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "validate", "build"])
    ap.add_argument("--agent", default="claude-code")
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--tasks", default="all")
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--out", default=str(ROOT / "results"))
    a = ap.parse_args()
    tasks = all_tasks() if a.tasks == "all" else a.tasks.split(",")
    out_root = Path(a.out)
    ensure_infra()
    for t in tasks:
        build_task(load_task(t))
    if a.mode == "build":
        return
    if a.mode == "validate":
        bad = 0
        for t in tasks:
            msg = validate_one(t, out_root)
            print(f"[{t}] {msg}")
            bad += "FAIL" in msg or "failed" in msg
        sys.exit(1 if bad else 0)
    secrets = load_env()
    jobs = [(t, i) for t in tasks for i in range(1, a.trials + 1)]
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = {ex.submit(run_one, a.agent, a.model, t, i, secrets, out_root): (t, i) for t, i in jobs}
        for f in cf.as_completed(futs):
            t, i = futs[f]
            try:
                print(f"[{t}#{i}] {f.result()}", flush=True)
            except Exception as e:
                print(f"[{t}#{i}] ERROR {e}", flush=True)


if __name__ == "__main__":
    main()
