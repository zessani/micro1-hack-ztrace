import argparse
import gzip
import ipaddress
import json
import posixpath
import re
import sys
import tomllib
from pathlib import Path

TRACER_VERSION = "0.1"
REPO_ROOT = "/work/repo"
REPORT_PATH = "/work/report.json"
SHELLS = {"bash", "sh", "dash", "zsh"}
OUTPUT_CAP = 64 * 1024
EXCLUDED_PREFIXES = ("/dev/", "/proc/", "/sys/")
CLONE_CALLS = {"clone", "clone3", "fork", "vfork"}
EXEC_CALLS = {"execve", "execveat"}
WRITE_FLAGS = ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC")
FAIL_RESULTS = {
    "ECONNREFUSED": "refused",
    "ETIMEDOUT": "timeout",
    "ENETUNREACH": "unreachable",
    "EHOSTUNREACH": "unreachable",
}
LINUX_ERRNO = {111: "ECONNREFUSED", 110: "ETIMEDOUT", 101: "ENETUNREACH", 113: "EHOSTUNREACH", 104: "ECONNRESET"}
ESCAPES = {"n": 10, "t": 9, "r": 13, "v": 11, "f": 12, "a": 7, "b": 8, "e": 27, "\\": 92, '"': 34, "'": 39}

LINE_RE = re.compile(r"^(\d+)\s+(\d+(?:\.\d+)?)\s(.*)$")
CALL_RE = re.compile(r"^([a-z_][a-z0-9_]*)\(")
RESUMED_RE = re.compile(r"^<\.\.\. ([a-z0-9_]+) resumed>\s?(.*)$")
EXITED_RE = re.compile(r"^\+\+\+ exited with (\d+) \+\+\+")
KILLED_RE = re.compile(r"^\+\+\+ killed by (SIG[A-Z0-9]+)")
SUPERSEDED_RE = re.compile(r"^\+\+\+ superseded by execve in pid (\d+) \+\+\+")
RET_RE = re.compile(r"^=\s+(-?\d+|0x[0-9a-fA-F]+|\?)(?:<(.*?)>)?(?:\s+(E[A-Z0-9]+))?")
FD_RE = re.compile(r"^(-?\d+|AT_FDCWD)(?:<(.*)>)?$")
INET_RE = re.compile(r'sa_family=AF_INET,\s*sin_port=htons\((\d+)\),\s*sin_addr=inet_addr\("([^"]+)"\)')
INET6_RE = re.compile(r'sa_family=AF_INET6,\s*sin6_port=htons\((\d+)\).*?inet_pton\(AF_INET6,\s*"([^"]+)"')
SOCK_DECO_RE = re.compile(r"^([A-Za-z0-9]+):\[(\d+)\]$")
DECO_PROTO = {"TCP": "tcp", "TCPv6": "tcp", "UDP": "udp", "UDPv6": "udp", "UNIX": "unix"}
UNFINISHED = " <unfinished ...>"


def skip_string(s, i):
    n = len(s)
    j = i + 1
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
        elif c == '"':
            return j + 1
        else:
            j += 1
    return n


def split_args(s):
    parts = []
    start = 0
    depth = 0
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == '"':
            i = skip_string(s, i)
            continue
        if c == "<":
            j = s.find(">", i)
            i = n if j < 0 else j + 1
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                last = s[start:i].strip()
                if last or parts:
                    parts.append(last)
                return parts, i
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(s[start:i].strip())
            start = i + 1
        i += 1
    last = s[start:].strip()
    if last:
        parts.append(last)
    return parts, n


def cstring(raw):
    raw = raw.strip()
    if not raw.startswith('"'):
        return None
    out = bytearray()
    i = 1
    n = len(raw)
    while i < n:
        c = raw[i]
        if c == '"':
            break
        if c == "\\" and i + 1 < n:
            d = raw[i + 1]
            if d == "x":
                out.append(int(raw[i + 2:i + 4], 16))
                i += 4
            elif d in "01234567":
                j = i + 1
                while j < n and j < i + 4 and raw[j] in "01234567":
                    j += 1
                out.append(int(raw[i + 1:j], 8) & 0xFF)
                i = j
            else:
                out.append(ESCAPES.get(d, ord(d) & 0xFF))
                i += 2
            continue
        out += c.encode()
        i += 1
    return bytes(out)


def text(raw):
    b = cstring(raw)
    return None if b is None else b.decode("utf-8", "backslashreplace")


def string_list(raw):
    raw = raw.strip()
    if not raw.startswith("["):
        return None
    items, _ = split_args(raw[1:])
    return [t for t in (text(x) for x in items) if t is not None]


def iov_data(raw):
    out = bytearray()
    i = raw.find("iov_base=")
    while i >= 0:
        j = i + len("iov_base=")
        if raw.startswith('"', j):
            end = skip_string(raw, j)
            out += cstring(raw[j:end]) or b""
            i = raw.find("iov_base=", end)
        else:
            i = raw.find("iov_base=", j)
    return bytes(out)


def fd_arg(raw):
    m = FD_RE.match(raw.strip())
    if not m:
        return None, None
    fd = m.group(1)
    return (fd if fd == "AT_FDCWD" else int(fd)), m.group(2)


class Call:
    __slots__ = ("pid", "t", "name", "args", "ret", "ret_deco", "err", "raw_args")

    def __init__(self, pid, t, name, args, raw_args, ret, ret_deco, err):
        self.pid = pid
        self.t = t
        self.name = name
        self.args = args
        self.raw_args = raw_args
        self.ret = ret
        self.ret_deco = ret_deco
        self.err = err

    @property
    def ok(self):
        return self.ret is not None and self.ret >= 0 and self.err is None


def parse_call(pid, t, body):
    m = CALL_RE.match(body)
    if not m:
        return None
    name = m.group(1)
    rest = body[m.end():]
    args, end = split_args(rest)
    ret_text = rest[end + 1:].strip()
    rm = RET_RE.match(ret_text)
    ret = deco = err = None
    if rm:
        v = rm.group(1)
        if v != "?":
            ret = int(v, 16) if v.startswith("0x") else int(v)
        deco = rm.group(2)
        err = rm.group(3)
    return Call(pid, t, name, args, rest[:end], ret, deco, err)


def read_lines(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="surrogateescape") as f:
        for line in f:
            yield line.rstrip("\n")


def scan(lines):
    records = []
    pending = {}
    first_seen = {}
    parent_of = {}
    for line in lines:
        m = LINE_RE.match(line)
        if not m:
            continue
        pid = int(m.group(1))
        t = float(m.group(2))
        rest = m.group(3)
        first_seen.setdefault(pid, t)
        if rest.startswith("+++"):
            sm = SUPERSEDED_RE.match(rest)
            if sm:
                other = int(sm.group(1))
                if other in pending:
                    pending[pid] = pending.pop(other)
                continue
            em = EXITED_RE.match(rest)
            if em:
                records.append(("exit", pid, t, int(em.group(1)), None))
                continue
            km = KILLED_RE.match(rest)
            if km:
                records.append(("exit", pid, t, None, km.group(1)))
            continue
        if rest.startswith("---"):
            continue
        rm = RESUMED_RE.match(rest)
        if rm:
            if pid not in pending:
                continue
            t, head = pending.pop(pid)
            rest = head + rm.group(2)
        if rest.endswith(UNFINISHED):
            pending[pid] = (t, rest[: -len(UNFINISHED)])
            continue
        call = parse_call(pid, t, rest)
        if call is None:
            continue
        records.append(("call", call))
        if call.name in CLONE_CALLS and call.ok and call.ret > 0:
            parent_of[call.ret] = (pid, "CLONE_THREAD" in call.raw_args, "CLONE_PARENT" in call.raw_args)
    return records, first_seen, parent_of


def resolve(base, path):
    if path.startswith("/"):
        return posixpath.normpath(path)
    return posixpath.normpath(posixpath.join(base or "/", path))


def norm_ip(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if addr.version == 6 and addr.ipv4_mapped:
        return str(addr.ipv4_mapped)
    return str(addr)


class Proc:
    def __init__(self, pid, ppid, t):
        self.pid = pid
        self.ppid = ppid
        self.argv = []
        self.cwd = None
        self.start_cwd = None
        self.exit_code = None
        self.exit_group = None
        self.signal = None
        self.scope = "agent"
        self.command_root_pid = None
        self.t_start = t
        self.t_end = None

    def to_json(self, t0):
        code = self.exit_code
        if code is None and self.signal is None:
            code = self.exit_group
        return {
            "pid": self.pid,
            "ppid": self.ppid,
            "argv": self.argv,
            "cwd": self.start_cwd,
            "exit_code": code,
            "signal": self.signal,
            "scope": self.scope,
            "command_root_pid": self.command_root_pid,
            "t_start": rel(self.t_start, t0),
            "t_end": rel(self.t_end, t0),
        }


def rel(t, t0):
    return None if t is None else round(t - t0, 6)


class Builder:
    def __init__(self, first_seen, parent_of, root_is_command, initial_cwd, hosts):
        self.first_seen = first_seen
        self.parent_of = parent_of
        self.root_is_command = root_is_command
        self.initial_cwd = initial_cwd
        self.hosts = hosts
        self.procs = {}
        self.tgid = {}
        self.file_events = []
        self.read_opens = []
        self.agent_read_opens = []
        self.read_seen = set()
        self.connections = []
        self.pending_conn = {}
        self.traced_sinks = set()
        self.sock_proto = {}
        self.outputs = {}
        self.t0 = min(first_seen.values()) if first_seen else 0.0
        roots = [pid for pid in first_seen if pid not in parent_of]
        self.root_pid = min(roots, key=first_seen.get) if roots else None

    def proc(self, tid):
        if tid in self.tgid:
            return self.procs[self.tgid[tid]]
        link = self.parent_of.get(tid)
        if link is None:
            p = Proc(tid, None, self.first_seen.get(tid))
            if tid == self.root_pid:
                p.cwd = p.start_cwd = self.initial_cwd
                if self.root_is_command:
                    p.scope = "command"
                    p.command_root_pid = tid
            self.procs[tid] = p
            self.tgid[tid] = tid
            return p
        parent_tid, is_thread, clone_parent = link
        parent = self.proc(parent_tid)
        if is_thread:
            self.tgid[tid] = parent.pid
            return parent
        ppid = parent.ppid if clone_parent else parent.pid
        p = Proc(tid, ppid, self.first_seen.get(tid))
        p.argv = list(parent.argv)
        p.cwd = p.start_cwd = parent.cwd
        p.scope = parent.scope
        p.command_root_pid = parent.command_root_pid
        self.procs[tid] = p
        self.tgid[tid] = tid
        return p

    def build(self, records):
        for rec in records:
            if rec[0] == "exit":
                _, tid, t, code, sig = rec
                p = self.proc(tid)
                if tid == p.pid:
                    p.exit_code = code
                    p.signal = sig
                    p.t_end = t
                continue
            call = rec[1]
            p = self.proc(call.pid)
            handler = getattr(self, "on_" + call.name, None)
            if handler:
                handler(p, call)
        for conn in self.pending_conn.values():
            if conn["result"] == "inprogress":
                conn["result"] = "inprogress_unknown"
        return self.facts()

    def base_dir(self, p, raw_fd):
        fd, deco = fd_arg(raw_fd)
        if fd == "AT_FDCWD":
            if deco:
                p.cwd = deco
            return p.cwd
        return deco

    def path_at(self, p, call, fd_index, path_index):
        if len(call.args) <= path_index:
            return None
        path = text(call.args[path_index])
        if path is None:
            return None
        base = p.cwd if fd_index is None else self.base_dir(p, call.args[fd_index])
        return resolve(base, path)

    def file_event(self, p, op, path, t):
        if p.scope != "command" or path is None:
            return
        if path == REPORT_PATH or path.startswith(EXCLUDED_PREFIXES):
            return
        self.file_events.append({"pid": p.pid, "op": op, "path": path, "t": rel(t, self.t0)})

    def on_execve(self, p, call, argv_index=1):
        if not call.ok:
            return
        argv = string_list(call.args[argv_index]) if len(call.args) > argv_index else None
        exe = text(call.args[argv_index - 1]) or ""
        p.argv = argv or [exe]
        p.start_cwd = p.cwd
        names = {posixpath.basename(exe)}
        if p.argv:
            names.add(posixpath.basename(p.argv[0]).lstrip("-"))
        parent = self.procs.get(p.ppid) if p.ppid is not None else None
        if p.scope == "agent" and parent is not None and parent.scope == "agent" and names & SHELLS:
            p.scope = "command"
            p.command_root_pid = p.pid

    def on_execveat(self, p, call):
        self.on_execve(p, call, argv_index=2)

    def on_chdir(self, p, call):
        if call.ok:
            p.cwd = self.path_at(p, call, None, 0)

    def on_fchdir(self, p, call):
        if call.ok and call.args:
            _, deco = fd_arg(call.args[0])
            if deco:
                p.cwd = deco

    def on_openat(self, p, call, fd_index=0, path_index=1, flags_index=2):
        if not call.ok or len(call.args) <= flags_index:
            return
        flags = call.args[flags_index]
        if any(f in flags for f in WRITE_FLAGS):
            self.write_open(p, call, fd_index, path_index)
        elif "O_DIRECTORY" not in flags:
            self.read_open(p, call, fd_index, path_index)

    def read_open(self, p, call, fd_index, path_index):
        path = self.path_at(p, call, fd_index, path_index)
        if path is None or not path.startswith(REPO_ROOT + "/"):
            return
        relp = path[len(REPO_ROOT) + 1:]
        parts = relp.split("/")
        if parts[0] == ".git" or "node_modules" in parts or "__pycache__" in parts:
            return
        key = (p.pid, path)
        if key in self.read_seen:
            return
        self.read_seen.add(key)
        dest = self.read_opens if p.scope == "command" else self.agent_read_opens
        dest.append({"pid": p.pid, "path": path, "t": rel(call.t, self.t0)})

    def on_open(self, p, call):
        self.on_openat(p, call, None, 0, 1)

    def on_creat(self, p, call):
        if call.ok:
            self.write_open(p, call, None, 0)

    def write_open(self, p, call, fd_index, path_index):
        path = self.path_at(p, call, fd_index, path_index)
        if p.scope == "command":
            self.traced_sinks.add(path)
            if call.ret_deco:
                self.traced_sinks.add(call.ret_deco)
        self.file_event(p, "write", path, call.t)

    def rename(self, p, call, src, dst):
        if call.ok:
            self.file_event(p, "rename_from", self.path_at(p, call, *src), call.t)
            self.file_event(p, "rename_to", self.path_at(p, call, *dst), call.t)

    def on_rename(self, p, call):
        self.rename(p, call, (None, 0), (None, 1))

    def on_renameat(self, p, call):
        self.rename(p, call, (0, 1), (2, 3))

    on_renameat2 = on_renameat

    def on_unlink(self, p, call):
        if call.ok:
            self.file_event(p, "unlink", self.path_at(p, call, None, 0), call.t)

    def on_unlinkat(self, p, call):
        if call.ok and not (len(call.args) > 2 and "AT_REMOVEDIR" in call.args[2]):
            self.file_event(p, "unlink", self.path_at(p, call, 0, 1), call.t)

    def on_mkdir(self, p, call):
        if call.ok:
            self.file_event(p, "mkdir", self.path_at(p, call, None, 0), call.t)

    def on_mkdirat(self, p, call):
        if call.ok:
            self.file_event(p, "mkdir", self.path_at(p, call, 0, 1), call.t)

    def socket_key(self, p, raw_fd):
        fd, deco = fd_arg(raw_fd)
        m = SOCK_DECO_RE.match(deco or "")
        if m is None:
            return (p.pid, fd)
        key = f"socket:[{m.group(2)}]"
        if m.group(1) in DECO_PROTO:
            self.sock_proto.setdefault(key, DECO_PROTO[m.group(1)])
        return key

    def on_socket(self, p, call):
        if not call.ok or len(call.args) < 2:
            return
        if call.args[0] in ("AF_UNIX", "AF_LOCAL"):
            proto = "unix"
        elif "SOCK_STREAM" in call.args[1]:
            proto = "tcp"
        elif "SOCK_DGRAM" in call.args[1]:
            proto = "udp"
        else:
            proto = "unknown"
        m = SOCK_DECO_RE.match(call.ret_deco or "")
        if m:
            self.sock_proto[f"socket:[{m.group(2)}]"] = proto

    def on_connect(self, p, call):
        if len(call.args) < 2:
            return
        key = self.socket_key(p, call.args[0])
        prior = self.pending_conn.get(key)
        if prior is not None and prior["result"] == "inprogress":
            if call.ok or call.err == "EISCONN":
                self.settle(key, None)
            elif call.err not in ("EALREADY", "EINPROGRESS"):
                self.settle(key, call.err)
            return
        m = INET_RE.search(call.args[1])
        family = "inet"
        if not m:
            m = INET6_RE.search(call.args[1])
            family = "inet6"
        if not m or p.scope != "command":
            return
        ip = norm_ip(m.group(2))
        proto = self.sock_proto.get(key, "unknown")
        if call.ok:
            result, err = ("udp_noop" if proto == "udp" else "ok"), None
        elif call.err == "EINPROGRESS":
            result, err = "inprogress", None
        elif call.ret is None:
            result, err = "inprogress", None
        else:
            result, err = FAIL_RESULTS.get(call.err, "unreachable"), call.err
        conn = {
            "pid": p.pid,
            "family": family,
            "proto": proto,
            "ip": ip,
            "port": int(m.group(1)),
            "host": self.hosts.get(ip),
            "result": result,
            "errno": err,
            "t": rel(call.t, self.t0),
        }
        self.connections.append(conn)
        if result == "inprogress":
            self.pending_conn[key] = conn

    def settle(self, key, err):
        conn = self.pending_conn.pop(key, None)
        if conn is None or conn["result"] != "inprogress":
            return
        if err is None:
            conn["result"] = "inprogress_ok"
        else:
            conn["result"] = "inprogress_failed"
            conn["errno"] = err

    def on_getsockopt(self, p, call):
        if not call.ok or len(call.args) < 4 or call.args[2] != "SO_ERROR":
            return
        key = self.socket_key(p, call.args[0])
        if key not in self.pending_conn:
            return
        val = call.args[3].strip("[]").strip()
        if val in ("0", ""):
            self.settle(key, None)
        elif val.isdigit():
            self.settle(key, LINUX_ERRNO.get(int(val), val))
        else:
            self.settle(key, val.split()[0])

    def on_write(self, p, call, data=None):
        if not call.args:
            return
        fd, deco = fd_arg(call.args[0])
        key = self.socket_key(p, call.args[0])
        if key in self.pending_conn:
            if call.ok:
                self.settle(key, None)
            elif call.err in FAIL_RESULTS:
                self.settle(key, call.err)
        if fd not in (1, 2) or p.scope != "command" or not call.ok:
            return
        if deco and (deco in self.traced_sinks or deco == "/dev/null"):
            return
        if data is None:
            data = cstring(call.args[1]) if len(call.args) > 1 else None
        if not data:
            return
        out = self.outputs.setdefault((p.pid, fd), {"head": bytearray(), "tail": bytearray(), "size": 0})
        out["size"] += len(data)
        room = OUTPUT_CAP - len(out["head"])
        if room > 0:
            out["head"] += data[:room]
        out["tail"] += data[-(OUTPUT_CAP // 2):]
        if len(out["tail"]) > OUTPUT_CAP // 2:
            del out["tail"][: len(out["tail"]) - OUTPUT_CAP // 2]

    def on_writev(self, p, call):
        self.on_write(p, call, iov_data(call.args[1]) if len(call.args) > 1 else b"")

    def on_exit_group(self, p, call):
        if call.args and call.args[0].lstrip("-").isdigit():
            p.exit_group = int(call.args[0]) & 0xFF

    def facts(self):
        procs = sorted(self.procs.values(), key=lambda p: (p.t_start or 0, p.pid))
        outputs = []
        for (pid, fd), out in self.outputs.items():
            truncated = out["size"] > OUTPUT_CAP
            if truncated:
                half = OUTPUT_CAP // 2
                body = bytes(out["head"][:half]) + b"\n[... truncated ...]\n" + bytes(out["tail"])
            else:
                body = bytes(out["head"])
            outputs.append({"pid": pid, "fd": fd, "text": body.decode("utf-8", "replace"), "truncated": truncated})
        return {
            "schema": "zbench.facts/1",
            "repo_root": REPO_ROOT,
            "root_pid": self.root_pid,
            "processes": [p.to_json(self.t0) for p in procs],
            "file_events": self.file_events,
            "read_opens": self.read_opens,
            "agent_read_opens": self.agent_read_opens,
            "connections": self.connections,
            "outputs": outputs,
            "tracer_version": TRACER_VERSION,
        }


def read_meta(trace_dir):
    meta = {}
    path = Path(trace_dir) / "ztrace.meta"
    if path.exists():
        for line in path.read_text().splitlines():
            k, _, v = line.partition("=")
            meta[k.strip()] = v
    return meta


def trace_file(trace_dir):
    d = Path(trace_dir)
    for name in ("trace.log", "trace.log.gz"):
        if (d / name).exists():
            return d / name
    raise FileNotFoundError(f"no trace.log or trace.log.gz in {trace_dir}")


def load_hosts(task_path):
    if not task_path:
        return {}
    with open(task_path, "rb") as f:
        task = tomllib.load(f)
    return {norm_ip(str(ip)): name for ip, name in task.get("hosts", {}).items()}


def build_facts(trace_dir, task_path=None, root_is_command=False):
    meta = read_meta(trace_dir)
    root_cmd = root_is_command or meta.get("root_is_command") == "1"
    records, first_seen, parent_of = scan(read_lines(trace_file(trace_dir)))
    builder = Builder(first_seen, parent_of, root_cmd, meta.get("cwd") or REPO_ROOT, load_hosts(task_path))
    return builder.build(records)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m tracer.parse")
    ap.add_argument("trace_dir")
    ap.add_argument("--task")
    ap.add_argument("--root-is-command", action="store_true")
    ap.add_argument("-o", "--output")
    args = ap.parse_args(argv)
    facts = build_facts(args.trace_dir, args.task, args.root_is_command)
    data = json.dumps(facts, indent=1, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(data + "\n")
    else:
        sys.stdout.write(data + "\n")


if __name__ == "__main__":
    main()
