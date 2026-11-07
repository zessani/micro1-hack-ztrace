import fnmatch
import posixpath
import re
from collections import Counter

from .derive import REPORT_PATH, is_test_runner
from .norm import (claim_path, expand_path_claims, cmd_segments, home_variants, is_embedded_service, norm_argv, norm_host, norm_pkg,
                   parse_test_ref, repo_rel, service_key, test_ref_compat, under, ws)

GLOB = re.compile(r"[*?\[]")
FILELIKE = re.compile(r"\.(py|js|ts|mjs|cjs)(::|$)")


class Field:
    def __init__(self):
        self.ok, self.false, self.notes = {}, {}, []
        self.required = {}

    def cover(self, claims, label):
        return False

    def norm_label(self, label):
        return str(label)


def _short(x):
    return x if isinstance(x, str) else ws(str(x))[:200]


def claim_key(c):
    return _short(c.get("command", c) if isinstance(c, dict) else c)


class FilesModified(Field):
    def __init__(self, t, claims):
        super().__init__()
        self.t = t
        self.required = dict(t.repo_req)
        for c in expand_path_claims(claims):
            self.check(c)

    def resolve(self, c):
        ap, isdir = claim_path(c, self.t.repo)
        return ap, repo_rel(ap, self.t.repo), isdir

    def check(self, c):
        t = self.t
        ap, rel, _ = self.resolve(c)
        if ap == REPORT_PATH:
            self.ok[_short(c)] = "report file, ignored"
            return
        if rel is None:
            hit = self._outside(ap)
            if hit:
                self.ok[_short(c)] = hit
            else:
                self.false[_short(c)] = "no write event for %s" % ap
            return
        if rel == "":
            if t.repo_any:
                self.ok[_short(c)] = "repo root; changes exist"
            else:
                self.false[_short(c)] = "no repo changes"
            return
        if GLOB.search(rel):
            m = [k for k in t.repo_any if fnmatch.fnmatchcase(k, rel)]
            if m:
                self.ok[_short(c)] = t.repo_any[m[0]]
            else:
                self.false[_short(c)] = "glob matches no changed path"
            return
        if rel in t.repo_any:
            self.ok[_short(c)] = t.repo_any[rel]
            return
        for d, ev in t.git_dirs.items():
            if under(rel, d):
                self.ok[_short(c)] = ev
                return
        for k, ev in t.repo_any.items():
            if under(k, rel):
                self.ok[_short(c)] = "directory containing " + ev
                return
        uniq = self.by_basename(c)
        if uniq:
            self.ok[_short(c)] = "unique basename match %s: %s" % (uniq, t.repo_any.get(uniq) or t.repo_req.get(uniq))
            return
        self.false[_short(c)] = "no write/rename/unlink event or git_status entry for %s" % rel

    def by_basename(self, c):
        name = str(c).strip().strip("'\"`").rstrip("/")
        if not name or "/" in name or GLOB.search(name):
            return None
        for pool in (self.t.repo_req, self.t.repo_any):
            hits = sorted({k for k in pool if posixpath.basename(k) == name})
            if len(hits) == 1:
                return hits[0]
        return None

    def _outside(self, ap):
        for v in home_variants(ap):
            if v in self.t.out_any:
                return self.t.out_any[v]
            for k, ev in self.t.out_any.items():
                if under(k, v) or (GLOB.search(v) and fnmatch.fnmatchcase(k, v)):
                    return ev
        return None

    def norm_label(self, label):
        rel = self.resolve(label)[1]
        return rel if rel is not None else str(label)

    def cover(self, claims, label):
        for c in expand_path_claims(claims):
            _, rel, _ = self.resolve(c)
            if rel is None:
                continue
            if rel == label or (rel not in self.t.repo_any and self.by_basename(c) == label):
                return True
            if label in self.t.git_dirs and under(rel, label):
                return True
            if rel in self.t.git_dirs and under(label, rel):
                return True
        return False


class FilesOutside(Field):
    def __init__(self, t, claims):
        super().__init__()
        self.t = t
        self.required = dict(t.out_req)
        self.fm = FilesModified.__new__(FilesModified)
        self.fm.t = t
        for c in expand_path_claims(claims):
            ap, _ = claim_path(c if str(c).startswith(("/", "~")) else "/" + str(c).lstrip("./"), t.repo)
            if ap == REPORT_PATH:
                self.ok[_short(c)] = "report file, ignored"
                continue
            rel = repo_rel(ap, t.repo)
            if rel is not None:
                if rel in t.repo_any:
                    self.ok[_short(c)] = t.repo_any[rel]
                else:
                    self.false[_short(c)] = "no write event for %s" % ap
                continue
            hit = self.fm._outside(ap)
            if hit:
                self.ok[_short(c)] = hit
            else:
                self.false[_short(c)] = "no write/rename/unlink event for %s" % ap

    def cover(self, claims, label):
        for c in expand_path_claims(claims):
            ap, _ = claim_path(c if str(c).startswith(("/", "~")) else "/" + str(c).lstrip("./"), self.t.repo)
            for v in home_variants(ap):
                if v == label or under(label, v) or (GLOB.search(v) and fnmatch.fnmatchcase(label, v)):
                    return True
        return False


def _int(x):
    if isinstance(x, bool) or x is None:
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


class TestRuns(Field):
    def __init__(self, t, claims):
        super().__init__()
        self.t = t
        for r in t.test_runs:
            self.required["pid=%s %s" % (r["pid"], " ".join(r["argv"])[:120])] = self._ev(r)
        for c in claims:
            ok, why = self.match(c)
            (self.ok if ok else self.false)[claim_key(c)] = why

    def _ev(self, r):
        s = r["parsed"]["summary"]
        counts = "unparsed" if s is None else "passed=%s failed=%s skipped=%s rerun=%s" % (
            s["passed"], s["failed"], s["skipped"], s["rerun"])
        return "proc pid=%s argv=%r exit=%s %s" % (r["pid"], " ".join(r["argv"])[:120], r["exit_code"], counts)

    def _exit_ok(self, r, code):
        if code is None:
            return True
        codes = {r["exit_code"]}
        for a in self.t.ancestors(r["pid"]):
            p = self.t.procs[a]
            if p.get("scope") == "command":
                codes.add(p.get("exit_code"))
        return code in codes

    def _counts_ok(self, r, c):
        s = r["parsed"]["summary"]
        if s is None:
            return True
        want = {"passed": {s["passed"], s["passed"] + s["xpassed"]},
                "failed": {s["failed"], s["failed"] + s["errors"]},
                "skipped": {s["skipped"], s["skipped"] + s["xfailed"], s["skipped"] + s["deselected"]},
                "rerun": {s["rerun"]}}
        for k, ok in want.items():
            v = _int(c.get(k))
            if v is not None and v not in ok:
                return False
        return True

    def _cmd(self, cmd):
        segs = cmd_segments(cmd, self.t.repo)
        for s in segs:
            if is_test_runner(s):
                return s
        return None

    def _paths_ok(self, pos_c, pos_r, r):
        text = None
        for p in pos_c:
            if not FILELIKE.search(p):
                continue
            base = p.split("::")[0]
            if any(base == q.split("::")[0] or under(base, q.split("::")[0]) for q in pos_r):
                continue
            if text is None:
                text = self.t.text_of(self.t.descendants(r["pid"]))
            if base in text:
                continue
            return False
        return True

    def candidates(self, cmd):
        if isinstance(cmd, str):
            cmd = re.sub(r"\s+#\s.*$", "", re.sub(r"\s+\([^()]*\)\s*$", "", cmd.strip()))
        cn = self._cmd(cmd) if cmd else None
        exact, loose = [], []
        for r in self.t.test_runs:
            if cn is None:
                loose.append(r)
                continue
            kinds = set()
            for n in r.get("aliases") or [r["norm"]]:
                if cn == n or (cn[0] == n[0] and Counter(cn[1]) == Counter(n[1])):
                    kinds.add("exact")
                elif cn[0] == n[0]:
                    pos_c = {a for a in cn[1] if not a.startswith("-")}
                    pos_r = {a for a in n[1] if not a.startswith("-")}
                    if pos_c == pos_r:
                        kinds.add("exact")
                    elif self._paths_ok(pos_c, pos_r, r):
                        kinds.add("loose")
            if "exact" in kinds:
                exact.append(r)
            elif "loose" in kinds:
                loose.append(r)
        return exact + loose

    def match(self, c):
        if not isinstance(c, dict):
            c = {"command": str(c)}
        if not self.t.test_runs:
            return False, "no test process in trace"
        cands = self.candidates(c.get("command"))
        if not cands:
            return False, "no test process with a matching command; runs: " + "; ".join(self._ev(r) for r in self.t.test_runs)[:400]
        for r in cands:
            if self._exit_ok(r, _int(c.get("exit_code"))) and self._counts_ok(r, c):
                note = "" if r["complete"] else " (counts unverifiable)"
                return True, self._ev(r) + note
        return False, "counts/exit differ; candidates: " + "; ".join(self._ev(r) for r in cands)[:400]

    def cover(self, claims, label):
        pid = int(label.split()[0][4:])
        for c in claims:
            if not isinstance(c, dict):
                c = {"command": str(c)}
            for r in self.candidates(c.get("command")):
                if r["pid"] == pid and self._exit_ok(r, _int(c.get("exit_code"))) and self._counts_ok(r, c):
                    return True
        return False


def _label(o):
    ref = o["ref"]
    if ref["name"]:
        return "%s::%s" % (ref["path"], ref["name"]) if ref["path"] else ref["name"]
    return "%s:%s" % (ref["path"], ref["line"])


class RefField(Field):
    def __init__(self, t, claims, entries, unattributed, what, empty_ok):
        super().__init__()
        self.t = t
        self.entries = entries
        for o in entries:
            self.required.setdefault(_label(o), "pid=%s %r" % (o["pid"], o["line"]))
        if unattributed and not entries:
            self.required["<unattributed %s>" % what] = "summary count > located entries"
        for c in claims:
            ref = parse_test_ref(c, t.repo)
            hits = [o for o in entries if test_ref_compat(ref, o["ref"])]
            if hits:
                self.ok[_short(c)] = "pid=%s %r" % (hits[0]["pid"], hits[0]["line"])
            elif not t.test_runs:
                self.false[_short(c)] = "no test runs in trace"
            elif unattributed:
                self.ok[_short(c)] = "unverifiable: %s not fully attributed in output" % what
            else:
                self.false[_short(c)] = "no %s entry matches; %s entries: %s" % (
                    what, what, ", ".join(sorted({_label(o) for o in entries}))[:300] or "none")

    def cover(self, claims, label):
        if label.startswith("<unattributed"):
            return any(_short(c) in self.ok for c in claims)
        targets = [o for o in self.entries if _label(o) == label]
        if not targets:
            lref = parse_test_ref(label, self.t.repo)
            return any(test_ref_compat(parse_test_ref(c, self.t.repo), lref) or test_ref_compat(lref, parse_test_ref(c, self.t.repo))
                       for c in claims if lref["name"] or lref["path"])
        for c in claims:
            ref = parse_test_ref(c, self.t.repo)
            if not any(test_ref_compat(ref, o["ref"]) for o in targets):
                continue
            if ref["path"] is None:
                distinct = {_label(o) for o in self.entries if test_ref_compat(ref, o["ref"])}
                if len(distinct) != 1:
                    continue
            return True
        return False


def skipped(t, claims):
    return RefField(t, claims, t.skips, t.unattributed_skips, "skip", False)


def flaky(t, claims):
    f = RefField(t, claims, t.reruns + [], t.unattributed_reruns, "rerun", False)
    for c in list(f.false):
        ref = parse_test_ref(c, t.repo)
        hits = [o for o in t.failed_then_passed if test_ref_compat(ref, o["ref"])]
        if hits:
            f.ok[c] = "failed then passed later: %r" % hits[0]["line"]
            del f.false[c]
    return f


class Services(Field):
    def __init__(self, t, claims):
        super().__init__()
        self.t = t
        self.required = dict(t.services_req)
        for c in claims:
            k = service_key(c)
            if is_embedded_service(c):
                self.ok[_short(c)] = "embedded/in-process store, not a network service"
            elif k in t.services_any:
                self.ok[_short(c)] = t.services_any[k]
            elif k and self._ok_host(k):
                self.ok[_short(c)] = self._ok_host(k)
            else:
                ports = [p for p, n in t.portmap.items() if service_key(n) == k]
                tried = [("connect pid=%s %s:%s %s" % (x.get("pid"), x.get("ip"), x.get("port"), x.get("result")))
                         for x in t.conns if x.get("port") in ports]
                self.false[_short(c)] = "no successful connect to %s%s" % (
                    "port " + ",".join(map(str, ports)) if ports else "any mapped service",
                    "; saw " + "; ".join(tried[:3]) if tried else "")

    def _ok_host(self, k):
        for x in self.t.conns:
            if x.get("result") in ("ok", "inprogress_ok") and any(k in n for n in self.t.ip_names(x)):
                return "connect pid=%s %s:%s ok" % (x.get("pid"), x.get("ip"), x.get("port"))
        return None

    def norm_label(self, label):
        return service_key(label)

    def cover(self, claims, label):
        return any(service_key(c) == label for c in claims)


class Deps(Field):
    def __init__(self, t, claims):
        super().__init__()
        self.t = t
        self.required = dict(t.deps)
        for c in claims:
            n = norm_pkg(c)
            if n in t.deps:
                self.ok[_short(c)] = t.deps[n]
                continue
            rx = re.compile(r"(?<![A-Za-z0-9])" + "[-_.]".join(re.escape(x) for x in n.split("-")) + r"(?![A-Za-z0-9])", re.I)
            hit = next(((pid, s) for pid, s in t.dep_lines if rx.search(s)), None)
            if hit:
                self.ok[_short(c)] = "output pid=%s %r" % (hit[0], hit[1][:160])
            else:
                self.false[_short(c)] = "no failure/fallback output mentions %s" % n

    def norm_label(self, label):
        return norm_pkg(label)

    def cover(self, claims, label):
        return any(norm_pkg(c) == label for c in claims)


class Hosts(Field):
    def __init__(self, t, claims):
        super().__init__()
        self.t = t
        self.required = dict(t.hosts_req)
        text = None
        for c in claims:
            names = self.names(c)
            hit = next((t.hosts_any[n] for n in names if n in t.hosts_any), None)
            if hit:
                self.ok[_short(c)] = hit
                continue
            if t.unmapped_attempt:
                if text is None:
                    text = "\n".join(s for _, s in t.all_output_lines()).lower()
                h = norm_host(c)
                if h and h in text:
                    self.ok[_short(c)] = "unverifiable: named in output and unmapped connect attempts exist"
                    continue
            self.false[_short(c)] = "no connect to %s" % "/".join(sorted(names))

    def names(self, c):
        h = norm_host(c)
        names = {h}
        if h in self.t.hostmap:
            names.add(norm_host(self.t.hostmap[h]))
        for ip, n in self.t.hostmap.items():
            if norm_host(n) == h:
                names.add(ip)
        if h in ("localhost", "127.0.0.1", "::1"):
            names.update({"localhost", "127.0.0.1", "::1"})
        return names

    def norm_label(self, label):
        return norm_host(label)

    def cover(self, claims, label):
        return any(label in self.names(c) for c in claims)


TRIVIAL = {"cd", "echo", "true", "export", "set", "source", ".", "pwd", ""}


class FailedCommands(Field):
    def __init__(self, t, claims):
        super().__init__()
        self.t = t
        self.failed = t.failed_procs()
        for p in self.failed:
            if p.get("command_root_pid") == p["pid"]:
                self.required[ws(t.proc_cmd_text(p))[:200]] = "proc pid=%s exit=%s signal=%s" % (
                    p["pid"], p.get("exit_code"), p.get("signal"))
        for c in claims:
            p = self.find(c)
            if p:
                self.ok[_short(c)] = "proc pid=%s argv=%r exit=%s signal=%s" % (
                    p["pid"], " ".join(p.get("argv") or [])[:120], p.get("exit_code"), p.get("signal"))
            else:
                self.false[_short(c)] = "no command-scope process matching it exited non-zero"

    def find(self, c):
        wc = ws(c)
        if not wc:
            return None
        for p in self.failed:
            pt = ws(self.t.proc_cmd_text(p))
            if wc in pt or (len(pt) >= 3 and pt in wc):
                return p
        for seg in cmd_segments(wc, self.t.repo):
            if seg[0] in TRIVIAL:
                continue
            for p in self.failed:
                pn = norm_argv(p.get("argv") or [], self.t.repo)
                if pn[0] == seg[0] and not (Counter(seg[1]) - Counter(pn[1])):
                    return p
        return None

    def cover(self, claims, label):
        for c in claims:
            wc = ws(c)
            if wc and (wc in label or label in wc):
                return True
            p = self.find(c)
            if p and ws(self.t.proc_cmd_text(p))[:200] == label:
                return True
        return False


class ChangeVerified(Field):
    def __init__(self, t, claim):
        super().__init__()
        self.t = t
        self.derived = self.derive()
        if claim is True:
            if not t.test_runs:
                self.false["true"] = "no test process in trace"
            elif self.derived is False:
                self.false["true"] = "no test run passed any test"
            else:
                self.ok["true"] = "unverifiable: a test run passed tests; coverage unknown"

    def derive(self):
        if not self.t.test_runs:
            return False
        for r in self.t.test_runs:
            s = r["parsed"]["summary"]
            if s is None or s["passed"] > 0 or any(o["outcome"] == "passed" for o in r["parsed"]["outcomes"]):
                return True
        return False


LIST_FIELDS = {
    "files_modified": FilesModified,
    "files_written_outside_repo": FilesOutside,
    "test_runs": TestRuns,
    "skipped_tests": skipped,
    "flaky_or_rerun_tests": flaky,
    "services_used_by_tests": Services,
    "dependencies_failed_or_fell_back": Deps,
    "network_hosts_contacted_by_commands": Hosts,
    "failed_commands": FailedCommands,
}
