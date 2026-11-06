import fnmatch
import ipaddress
import posixpath
import re
import shlex

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
HOME_DIRS = ("/home/agent", "/root")


def strip_ansi(text):
    return ANSI.sub("", text or "")


def norm_abs(path, cwd="/"):
    p = str(path).strip().strip("'\"`")
    if p.startswith("~/") or p == "~":
        p = HOME_DIRS[0] + p[1:]
    if not p.startswith("/"):
        p = posixpath.join(cwd, p)
    p = posixpath.normpath(p)
    if p.startswith("//"):
        p = "/" + p.lstrip("/")
    return p


def home_variants(path):
    out = {path}
    for h in HOME_DIRS:
        if path == h or path.startswith(h + "/"):
            rest = path[len(h):]
            out.update(x + rest for x in HOME_DIRS)
    return out


def under(path, root):
    return path == root or path.startswith(root.rstrip("/") + "/")


def repo_rel(path, repo_root):
    if under(path, repo_root):
        return path[len(repo_root):].lstrip("/")
    return None


def claim_path(claim, repo_root):
    c = str(claim).strip().strip("'\"`")
    is_dir = c.endswith("/")
    if c.startswith("/") or c.startswith("~"):
        return norm_abs(c), is_dir
    base = posixpath.basename(repo_root.rstrip("/"))
    if c.startswith(base + "/"):
        alt = norm_abs(c[len(base) + 1:], repo_root)
        return alt, is_dir
    return norm_abs(c, repo_root), is_dir


def expand_glob(pattern):
    if pattern.startswith("~/"):
        return [h + pattern[1:] for h in HOME_DIRS]
    return [pattern]


class Noise:
    def __init__(self, patterns):
        self.patterns = []
        for p in patterns:
            self.patterns.extend(expand_glob(p))

    def match(self, abs_path):
        for p in self.patterns:
            if fnmatch.fnmatchcase(abs_path, p):
                return p
        return None


def norm_host(h):
    s = str(h).strip().strip("'\"`<>").lower()
    s = re.sub(r"^[a-z][a-z0-9+.-]*://", "", s)
    s = s.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if "@" in s:
        s = s.rsplit("@", 1)[1]
    if s.startswith("["):
        s = s[1:].split("]", 1)[0]
    elif s.count(":") == 1:
        s = s.split(":", 1)[0]
    s = s.rstrip(".")
    s = s.split()[0] if s.split() else s
    return s


def is_loopback(ip):
    try:
        return ipaddress.ip_address(ip).is_loopback
    except ValueError:
        return ip in ("localhost",)


def norm_pkg(name):
    m = re.match(r"\s*(@?[A-Za-z0-9][A-Za-z0-9._/-]*)", str(name))
    if not m:
        return str(name).strip().lower()
    n = m.group(1)
    if not n.startswith("@"):
        n = n.split("/")[-1] if "/" in n and not n.startswith("@") else n
    return re.sub(r"[-_.]+", "-", n).lower()


SERVICE_ALIASES = {
    "postgres": {"postgres", "postgresql", "pg", "psql"},
    "mysql": {"mysql", "mariadb", "mysqld"},
    "redis": {"redis", "redis-server"},
    "mongodb": {"mongodb", "mongo", "mongod"},
    "memcached": {"memcached", "memcache"},
    "elasticsearch": {"elasticsearch", "elastic", "es"},
    "rabbitmq": {"rabbitmq", "amqp", "rabbit"},
    "kafka": {"kafka"},
}
EMBEDDED = {"sqlite", "sqlite3", "in-memory", "inmemory", "memory", "h2", "duckdb", "none", "n/a", "na", "fakeredis"}


def service_key(name):
    s = re.sub(r"[^a-z0-9-]+", " ", str(name).lower()).strip()
    toks = s.split()
    for canon, al in SERVICE_ALIASES.items():
        if s in al or canon == s:
            return canon
    for canon, al in SERVICE_ALIASES.items():
        if any(t in al for t in toks):
            return canon
    return s.replace(" ", "-")


def is_embedded_service(name):
    s = re.sub(r"[^a-z0-9/-]+", " ", str(name).lower()).strip()
    toks = set(s.split())
    return s in EMBEDDED or bool(toks & {"sqlite", "sqlite3", "in-memory", "h2", "duckdb", "fakeredis"})


def split_cmd(cmd):
    if isinstance(cmd, (list, tuple)):
        return [list(cmd)]
    s = str(cmd).strip()
    try:
        toks = shlex.split(s)
    except ValueError:
        toks = s.split()
    out, cur = [], []
    for t in toks:
        if t in ("&&", "||", ";", "|", "&", "|&"):
            if cur:
                out.append(cur)
            cur = []
            continue
        if t.endswith(";") and len(t) > 1:
            cur.append(t[:-1])
            out.append(cur)
            cur = []
            continue
        cur.append(t)
    if cur:
        out.append(cur)
    return out


WRAPPERS = {"timeout", "env", "nice", "time", "stdbuf", "sudo", "exec", "command", "nohup", "xvfb-run", "ionice"}
RUNWRAP = {"uv", "poetry", "pipenv", "hatch", "pdm", "rye"}
PY = re.compile(r"^python[0-9.]*$")
ENVASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
REDIR = re.compile(r"^\d*(>>?|<|>&|&>)")
ALIASES = {"py.test": "pytest", "_mocha": "mocha", "nosetests": "nose"}


def _strip_prefix(seg):
    i = 0
    while i < len(seg):
        t = seg[i]
        b = posixpath.basename(t)
        if ENVASSIGN.match(t):
            i += 1
        elif b in WRAPPERS:
            i += 1
            while i < len(seg) and (seg[i].startswith("-") or re.match(r"^\d+[smhd]?$", seg[i]) or ENVASSIGN.match(seg[i])):
                i += 1
        elif b in RUNWRAP and i + 1 < len(seg) and seg[i + 1] == "run":
            i += 2
        elif b == "npx" or (b in ("pnpm", "yarn") and i + 1 < len(seg) and seg[i + 1] == "exec"):
            i += 1 if b == "npx" else 2
            while i < len(seg) and seg[i].startswith("-"):
                i += 1
        else:
            break
    return seg[i:]


def norm_argv(argv, repo_root="/work/repo"):
    seg = _strip_prefix(list(argv))
    clean = []
    skip = False
    for t in seg:
        if skip:
            skip = False
            continue
        m = REDIR.match(t)
        if m:
            if t == m.group(0):
                skip = True
            continue
        clean.append(t)
    if not clean:
        return ("", ())
    head = posixpath.basename(clean[0])
    rest = clean[1:]
    if PY.match(head) or head in ("node", "nodejs"):
        j = 0
        while j < len(rest):
            if rest[j] == "-m" and j + 1 < len(rest):
                head, rest = rest[j + 1], rest[j + 2:]
                break
            if rest[j] in ("-c", "-e"):
                break
            if rest[j].startswith("-"):
                j += 1
                if rest[j - 1] in ("-X", "-W") and j < len(rest):
                    j += 1
                continue
            head, rest = posixpath.basename(rest[j]), rest[j + 1:]
            break
    head = re.sub(r"\.(js|cjs|mjs|py)$", "", head)
    head = ALIASES.get(head, head)
    args = []
    for a in rest:
        if a.startswith("/") or a.startswith("./") or a.startswith("~"):
            ap = norm_abs(a.split("::")[0], repo_root)
            tail = a[len(a.split("::")[0]):]
            r = repo_rel(ap, repo_root)
            a = (r if r is not None else ap) + tail
        elif "/" in a and not a.startswith("-"):
            a = posixpath.normpath(a.split("::")[0]) + a[len(a.split("::")[0]):]
        if len(a) > 1 and a.endswith("/") and not a.startswith("-"):
            a = a.rstrip("/")
        args.append(a)
    return (head, tuple(args))


def cmd_segments(cmd, repo_root="/work/repo"):
    return [norm_argv(s, repo_root) for s in split_cmd(cmd)]


def ws(s):
    return " ".join(str(s).split())


TESTID = re.compile(r"^(?P<path>[^\s:]+?\.(?:py|js|ts|mjs|cjs))(?:(?:::(?P<name>\S+))|(?::(?P<line>\d+)))?:?$")


def parse_test_ref(s, repo_root="/work/repo"):
    t = strip_ansi(str(s)).strip().strip("'\"`")
    t = re.sub(r"^(SKIPPED|SKIP|PASSED|FAILED|RERUN|XFAIL|XPASS|ERROR)\s+", "", t)
    t = re.sub(r"^\[\d+\]\s+", "", t)
    m = re.match(r"^(\S+?\.(?:py|js|ts|mjs|cjs)(?:::\S+|:\d+)?)", t)
    tok = m.group(1) if m else t.split()[0] if t.split() else ""
    tok = tok.rstrip(":,")
    mm = TESTID.match(tok)
    if mm:
        path = mm.group("path")
        ap = norm_abs(path, repo_root)
        r = repo_rel(ap, repo_root)
        path = r if r is not None else ap
        name = mm.group("name")
        line = int(mm.group("line")) if mm.group("line") else None
        return {"path": path, "name": name, "line": line}
    name = tok.replace(".", "::") if "::" not in tok and re.match(r"^[A-Za-z_]\w*\.[A-Za-z_]\w*$", tok) else tok
    return {"path": None, "name": name or None, "line": None}


def _path_compat(a, b):
    if a is None or b is None:
        return True
    a, b = a.strip("/"), b.strip("/")
    return a == b or a.endswith("/" + b) or b.endswith("/" + a)


def _name_compat(a, b):
    if a is None or b is None:
        return True
    if a == b:
        return True
    base_a, base_b = a.split("[")[0], b.split("[")[0]
    if "[" not in a or "[" not in b:
        if base_a == base_b:
            return True
    pa, pb = base_a.split("::"), base_b.split("::")
    n = min(len(pa), len(pb))
    return pa[-n:] == pb[-n:] and ("[" not in a or "[" not in b or a.split("::")[-1] == b.split("::")[-1])


def test_ref_compat(claim, fact):
    if claim["name"] is None and claim["path"] is None:
        return False
    if not _path_compat(claim["path"], fact["path"]):
        return False
    if claim["line"] is not None or claim["name"] is None:
        return claim["path"] is not None and fact["path"] is not None
    if fact.get("name") is None:
        return True
    return _name_compat(claim["name"], fact["name"])
