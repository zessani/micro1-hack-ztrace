import copy
import json
import os

from grader.grade import grade_report, grade_run

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
RUN = os.path.join(FIX, "run_skip")
TASK = os.path.join(FIX, "task_skip")

EMPTY = {
    "files_modified": [], "files_written_outside_repo": [], "test_runs": [], "skipped_tests": [],
    "flaky_or_rerun_tests": [], "change_verified_by_tests": None, "services_used_by_tests": [],
    "dependencies_failed_or_fell_back": [], "network_hosts_contacted_by_commands": [], "failed_commands": [],
    "summary": "",
}


def load(name, base=RUN):
    with open(os.path.join(base, name)) as f:
        return json.load(f)


def honest():
    with open(os.path.join(TASK, "reference", "honest.json")) as f:
        return json.load(f)


def report(**kw):
    r = copy.deepcopy(EMPTY)
    r.update(kw)
    return r


def grade_fixture(rep, tool_texts=None):
    return grade_run(RUN, TASK, report=rep, tool_texts=tool_texts)


class Facts:
    def __init__(self):
        self.f = {"schema": "zbench.facts/1", "repo_root": "/work/repo", "root_pid": 1,
                  "processes": [{"pid": 1, "ppid": 0, "argv": ["claude"], "cwd": "/work/repo", "exit_code": 0,
                                 "signal": None, "scope": "agent", "command_root_pid": None, "t_start": 0, "t_end": 100}],
                  "file_events": [], "connections": [], "outputs": [], "tracer_version": "0.1"}
        self.next = 100
        self.t = 1.0

    def cmd(self, script, children=(), exit_code=0, signal=None):
        root = self.next
        self.next += 1
        self.t += 1
        self.f["processes"].append({"pid": root, "ppid": 1, "argv": ["bash", "-c", script], "cwd": "/work/repo",
                                    "exit_code": exit_code, "signal": signal, "scope": "command",
                                    "command_root_pid": root, "t_start": self.t, "t_end": self.t + 0.5})
        pids = []
        for ch in children:
            pid = self.next
            self.next += 1
            self.f["processes"].append({"pid": pid, "ppid": ch.get("ppid", root), "argv": ch["argv"], "cwd": "/work/repo",
                                        "exit_code": ch.get("exit", 0), "signal": ch.get("signal"), "scope": "command",
                                        "command_root_pid": root, "t_start": self.t + 0.1, "t_end": self.t + 0.4})
            if ch.get("out"):
                self.f["outputs"].append({"pid": pid, "fd": 1, "text": ch["out"], "truncated": ch.get("truncated", False)})
            for op, path in ch.get("files", []):
                self.f["file_events"].append({"pid": pid, "op": op, "path": path, "t": self.t + 0.2})
            for ip, port, res in ch.get("conns", []):
                self.f["connections"].append({"pid": pid, "family": "inet", "ip": ip, "port": port, "host": None,
                                              "result": res, "errno": None, "t": self.t + 0.3})
            pids.append(pid)
        return pids


def task(key, patterns=(), ports=None, hosts=None, noise=()):
    return {"id": "t", "key_field": key, "evidence_patterns": list(patterns), "ports": ports or {},
            "hosts": hosts or {}, "noise": {"ignore": list(noise)}}


def g(facts, rep, tsk, git=(), texts=None):
    return grade_report(rep, facts.f, {"git_status": list(git)}, tsk, None,
                        texts if texts is not None else [o["text"] for o in facts.f["outputs"]])
