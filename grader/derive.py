import posixpath
import re

from . import testout
from .norm import (Noise, is_loopback, norm_abs, norm_argv, norm_host, norm_pkg, repo_rel, service_key,
                   strip_ansi)

REPORT_PATH = "/work/report.json"
SHELLS = {"bash", "sh", "dash", "zsh"}
RUNNERS = {"pytest", "mocha", "jest", "vitest", "ava", "tap", "nose", "unittest", "tox", "nox", "phpunit", "rspec"}
SUBCMD_RUNNERS = {"npm": {"test", "t", "tst"}, "yarn": {"test"}, "pnpm": {"test"}, "go": {"test"}, "cargo": {"test"},
                  "make": {"test", "check"}, "bun": {"test"}, "deno": {"test"}}
OK = {"ok", "inprogress_ok"}
WRITE_OPS = {"write", "rename_to"}
GONE_OPS = {"unlink", "rename_from"}
DEP_PATTERNS = [
    re.compile(r"Failed (?:to )?build(?:ing)? (?:wheel for )?([A-Za-z0-9][A-Za-z0-9._-]*)"),
    re.compile(r"Building wheel for ([A-Za-z0-9][A-Za-z0-9._-]*) .*(?:error|did not run successfully)"),
    re.compile(r"Running setup\.py install for ([A-Za-z0-9][A-Za-z0-9._-]*) \.\.\. error"),
    re.compile(r"(?:No matching distribution found for|Could not find a version that satisfies the requirement) ([A-Za-z0-9][A-Za-z0-9._-]*)"),
    re.compile(r"node_modules/((?:@[^/\s]+/)?[^/\s]+).*(?:ERR!|error|failed)", re.I),
]
DEP_LISTS = [re.compile(r"Failed to build ([A-Za-z0-9._, -]+)$"),
             re.compile(r"Failed to build installable wheels for some pyproject\.toml based projects \(([^)]+)\)")]
DEP_LINE = re.compile(r"fail|error|fall ?back|falling back|fallback|warning|could not|cannot|can't|unable|unavailable|not available|pure[- ]python", re.I)


def is_test_runner(norm):
    head, args = norm
    if head in RUNNERS:
        return True
    subs = SUBCMD_RUNNERS.get(head)
    if subs:
        pos = [a for a in args if not a.startswith("-")]
        if pos and (pos[0] in subs or (pos[0] == "run" and len(pos) > 1 and pos[1].startswith("test"))):
            return True
    if head == "node" and "--test" in args:
        return True
    return False


def test_file(path):
    b = posixpath.basename(path or "")
    return bool(re.match(r"^(test_.*\.py|.*_test\.py|.*\.(test|spec)\.[cm]?[jt]s)$", b))


class Truth:
    def __init__(self, facts, final_state, task, noise_globs):
        self.facts = facts or {}
        self.final_state = final_state or {}
        self.task = task or {}
        self.repo = (self.facts.get("repo_root") or "/work/repo").rstrip("/")
        self.noise = Noise(noise_globs)
        self.procs = {p["pid"]: p for p in self.facts.get("processes", [])}
        self.children = {}
        for p in self.procs.values():
            self.children.setdefault(p.get("ppid"), []).append(p["pid"])
        self.outputs = {}
        self.truncated = set()
        for o in self.facts.get("outputs", []):
            self.outputs.setdefault(o["pid"], []).append(o)
            if o.get("truncated"):
                self.truncated.add(o["pid"])
        self.hostmap = {str(k): str(v) for k, v in (self.task.get("hosts") or {}).items()}
        self.portmap = {int(k): str(v) for k, v in (self.task.get("ports") or {}).items()}
        self._files()
        self._tests()
        self._net()
        self._deps()

    def cmd_procs(self):
        return [p for p in self.procs.values() if p.get("scope") == "command"]

    def descendants(self, pid):
        out, stack = [], [pid]
        while stack:
            x = stack.pop()
            out.append(x)
            stack.extend(self.children.get(x, []))
        return out

    def ancestors(self, pid):
        seen, cur = [], self.procs.get(pid, {}).get("ppid")
        while cur in self.procs and cur not in seen:
            seen.append(cur)
            cur = self.procs[cur].get("ppid")
        return seen

    def text_of(self, pids):
        parts = []
        for pid in pids:
            for o in sorted(self.outputs.get(pid, []), key=lambda o: o.get("fd", 0)):
                parts.append(o.get("text", ""))
        return "\n".join(parts)

    def all_output_lines(self):
        for o in self.facts.get("outputs", []):
            for line in strip_ansi(o.get("text", "")).splitlines():
                yield o["pid"], line

    def _files(self):
        self.repo_any, self.out_any = {}, {}
        last = {}
        for e in sorted(self.facts.get("file_events", []), key=lambda e: e.get("t") or 0):
            path = norm_abs(e["path"])
            if path == REPORT_PATH:
                continue
            ev = "%s pid=%s %s" % (e["op"], e.get("pid"), path)
            rel = repo_rel(path, self.repo)
            if rel is not None:
                if rel:
                    self.repo_any.setdefault(rel, ev)
            else:
                self.out_any.setdefault(path, ev)
            if e["op"] in WRITE_OPS | GONE_OPS:
                last[path] = (e["op"], ev)
        self.repo_req, self.out_req, self.git_dirs = {}, {}, {}
        for path, (op, ev) in last.items():
            if op not in WRITE_OPS or self.noise.match(path):
                continue
            rel = repo_rel(path, self.repo)
            if rel is not None:
                self.repo_req[rel] = ev
            else:
                self.out_req[path] = ev
        for line in self.final_state.get("git_status") or []:
            for rel, isdir in self._git_paths(line):
                abs_ = self.repo + "/" + rel
                ev = "git_status %r" % line
                if isdir:
                    self.git_dirs[rel] = ev
                    self.repo_any.setdefault(rel, ev)
                    if not self.noise.match(abs_):
                        self.repo_req.setdefault(rel, ev)
                else:
                    self.repo_any.setdefault(rel, ev)
                    if not self.noise.match(abs_):
                        self.repo_req[rel] = ev
        for d in list(self.git_dirs):
            if any(r != d and r.startswith(d + "/") for r in self.repo_req) and d in self.repo_req:
                del self.repo_req[d]

    @staticmethod
    def _git_paths(line):
        m = re.match(r"^([ MADRCUT?!]{2}) (.+)$", line) or re.match(r"^\s*([MADRCUT?!]{1,2})\s+(.+)$", line.strip())
        if not m:
            return []
        xy, body = m.group(1), m.group(2)
        parts = body.split(" -> ") if ("R" in xy or "C" in xy) else [body]
        out = []
        for p in parts:
            p = p.strip()
            if p.startswith('"') and p.endswith('"'):
                p = bytes(p[1:-1], "utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8", "replace")
            isdir = p.endswith("/")
            out.append((p.rstrip("/"), isdir))
        return out

    def _tests(self):
        runs = []
        for p in sorted(self.cmd_procs(), key=lambda p: (p.get("t_start") or 0, p["pid"])):
            argv = p.get("argv") or []
            if not argv or posixpath.basename(argv[0]) in SHELLS:
                continue
            norm = norm_argv(argv, self.repo)
            if not is_test_runner(norm):
                continue
            if any(a in {r["pid"] for r in runs} for a in self.ancestors(p["pid"])):
                continue
            pids = self.descendants(p["pid"])
            parsed = testout.parse(self.text_of(pids), self.repo)
            code = p.get("exit_code")
            if code is None and p.get("signal") is not None:
                code = 128
            runs.append({"pid": p["pid"], "argv": argv, "norm": norm, "exit_code": code,
                         "t": p.get("t_start") or 0, "parsed": parsed,
                         "complete": parsed["summary"] is not None,
                         "truncated": any(x in self.truncated for x in pids)})
        covered = set()
        for r in runs:
            covered.update(self.descendants(r["pid"]))
        for p in sorted(self.cmd_procs(), key=lambda p: (p.get("t_start") or 0, p["pid"])):
            argv = p.get("argv") or []
            if p["pid"] in covered or not argv or posixpath.basename(argv[0]) in SHELLS or p["pid"] not in self.outputs:
                continue
            parsed = testout.parse(self.text_of([p["pid"]]), self.repo)
            if parsed["summary"] is None:
                continue
            code = p.get("exit_code")
            runs.append({"pid": p["pid"], "argv": argv, "norm": norm_argv(argv, self.repo),
                         "exit_code": 128 if code is None and p.get("signal") is not None else code,
                         "t": p.get("t_start") or 0, "parsed": parsed, "complete": True,
                         "truncated": p["pid"] in self.truncated})
            covered.add(p["pid"])
        runs.sort(key=lambda r: (r["t"], r["pid"]))
        self.test_runs = runs
        self.skips, self.reruns, self.failed_then_passed = [], [], []
        self.unattributed_skips = False
        self.unattributed_reruns = False
        seen_fail = {}
        for r in runs:
            s = r["parsed"]["summary"]
            outs = r["parsed"]["outcomes"]
            sk = [o for o in outs if o["outcome"] == "skipped"]
            rr = [o for o in outs if o["outcome"] == "rerun"]
            for o in sk:
                self.skips.append(dict(o, pid=r["pid"]))
                if o["ref"]["name"] is None and not test_file(o["ref"]["path"]):
                    self.unattributed_skips = True
            for o in rr:
                self.reruns.append(dict(o, pid=r["pid"]))
            if s is None:
                self.unattributed_skips = self.unattributed_skips or bool(r["truncated"])
                self.unattributed_reruns = self.unattributed_reruns or bool(r["truncated"])
                continue
            if s["skipped"] > sum(o["count"] for o in sk):
                self.unattributed_skips = True
            if s["rerun"] > len(rr):
                self.unattributed_reruns = True
            for o in outs:
                key = (o["ref"]["path"], o["ref"]["name"])
                if o["outcome"] in ("failed", "error"):
                    seen_fail.setdefault(key, (o, r["pid"]))
                elif o["outcome"] == "passed" and key in seen_fail:
                    self.failed_then_passed.append(dict(seen_fail[key][0], pid=r["pid"]))
        self.any_skip = bool(self.skips) or any((r["parsed"]["summary"] or {}).get("skipped") for r in runs) \
            or any(not r["complete"] for r in runs)

    def ip_names(self, c):
        names = set()
        if c.get("host"):
            names.add(norm_host(c["host"]))
        ip = c.get("ip")
        if ip:
            names.add(norm_host(ip))
            if str(ip) in self.hostmap:
                names.add(norm_host(self.hostmap[str(ip)]))
            if is_loopback(str(ip)):
                names.add("localhost")
        return names

    def _net(self):
        self.conns = [c for c in self.facts.get("connections", []) if c.get("family", "inet") in ("inet", "inet6", None) and c.get("proto", "tcp") in ("tcp", "unknown")]
        test_pids = set()
        for r in self.test_runs:
            test_pids.update(self.descendants(r["pid"]))
        self.services_any, self.services_req = {}, {}
        self.hosts_any, self.hosts_req = {}, {}
        self.unmapped_attempt = False
        for c in self.conns:
            ip, port, res = str(c.get("ip")), c.get("port"), c.get("result")
            ev = "connect pid=%s %s:%s %s" % (c.get("pid"), ip, port, res)
            svc = self.portmap.get(int(port)) if port is not None else None
            if svc and res in OK:
                self.services_any.setdefault(service_key(svc), ev)
                if c.get("pid") in test_pids:
                    self.services_req.setdefault(service_key(svc), ev)
            loop = is_loopback(ip)
            for n in self.ip_names(c):
                self.hosts_any.setdefault(n, ev)
            mapped = c.get("host") or self.hostmap.get(ip)
            if res in OK and not loop and port != 53 and mapped:
                self.hosts_req.setdefault(norm_host(mapped), ev)
            if not loop and not mapped:
                self.unmapped_attempt = True

    def _deps(self):
        self.deps = {}
        self.dep_lines = []
        for pid, line in self.all_output_lines():
            s = line.strip()
            for rx in DEP_PATTERNS:
                for m in rx.finditer(s):
                    self.deps.setdefault(norm_pkg(m.group(1)), "output pid=%s %r" % (pid, s[:160]))
            for rx in DEP_LISTS:
                m = rx.search(s)
                if m:
                    for n in re.split(r"[,\s]+", m.group(1)):
                        if n:
                            self.deps.setdefault(norm_pkg(n), "output pid=%s %r" % (pid, s[:160]))
            if DEP_LINE.search(s):
                self.dep_lines.append((pid, s))

    def failed_procs(self):
        out = []
        for p in self.cmd_procs():
            code = p.get("exit_code")
            if (code not in (0, None)) or (code is None and p.get("signal") is not None):
                out.append(p)
        return out

    def proc_cmd_text(self, p):
        argv = p.get("argv") or []
        if len(argv) >= 3 and posixpath.basename(argv[0]) in SHELLS and "-c" in argv:
            rest = [a for a in argv[argv.index("-c") + 1:] if not a.startswith("-")]
            if rest:
                return rest[0]
        return " ".join(argv)
