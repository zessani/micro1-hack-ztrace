import re

from .norm import parse_test_ref, strip_ansi

WORDS = "passed|failed|skipped|errors?|xfailed|xpassed|rerun|warnings?|deselected"
PYSUM = re.compile(r"^=*\s*(?P<body>(?:\d+ (?:%s)(?:, )?)+|no tests ran)\s+in\s+[\d.]+\s*s\b.*$" % WORDS)
PAIR = re.compile(r"(\d+) (%s)" % WORDS)
SHORT = re.compile(r"^(PASSED|FAILED|ERROR|XFAIL|XPASS|RERUN)\s+(\S+)")
SKIPLOC = re.compile(r"^SKIPPED\s+\[(\d+)\]\s+(\S+?):(\d+):?\s*(.*)$")
SKIPID = re.compile(r"^SKIPPED\s+(\S+::\S+)")
VERBOSE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS|RERUN)\b")
XDIST = re.compile(r"^\[gw\d+\]\s+\[\s*\d+%\]\s+(PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS|RERUN)\s+(\S+)")
MOCHA = re.compile(r"^\s*(\d+) (passing|failing|pending)\b")
JEST = re.compile(r"^Tests:\s+(.*\btotal)")
OUTCOME = {"PASSED": "passed", "FAILED": "failed", "ERROR": "error", "XFAIL": "xfailed",
           "XPASS": "xpassed", "RERUN": "rerun", "SKIPPED": "skipped"}


def _counts(body):
    c = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "xfailed": 0, "xpassed": 0, "rerun": 0, "deselected": 0}
    for n, w in PAIR.findall(body):
        w = {"error": "errors", "warning": "warnings"}.get(w, w)
        if w in c:
            c[w] += int(n)
    return c


def parse(text, repo_root="/work/repo"):
    lines = strip_ansi(text).replace("\r", "\n").splitlines()
    summary = None
    framework = None
    outcomes = []
    mocha = {}
    for raw in lines:
        line = raw.strip()
        m = PYSUM.match(line)
        if m:
            summary = _counts(m.group("body"))
            framework = "pytest"
            continue
        m = SKIPLOC.match(line)
        if m:
            ref = parse_test_ref(m.group(2) + ":" + m.group(3), repo_root)
            outcomes.append({"outcome": "skipped", "ref": ref, "count": int(m.group(1)), "reason": m.group(4)[:200], "line": line[:300]})
            continue
        m = SKIPID.match(line)
        if m:
            outcomes.append({"outcome": "skipped", "ref": parse_test_ref(m.group(1), repo_root), "count": 1, "line": line[:300]})
            continue
        m = SHORT.match(line) or XDIST.match(line)
        if m:
            outcomes.append({"outcome": OUTCOME[m.group(1)], "ref": parse_test_ref(m.group(2), repo_root), "count": 1, "line": line[:300]})
            continue
        m = VERBOSE.match(line)
        if m:
            outcomes.append({"outcome": OUTCOME[m.group(2)], "ref": parse_test_ref(m.group(1), repo_root), "count": 1, "line": line[:300], "verbose": True})
            continue
        m = MOCHA.match(raw)
        if m:
            mocha[m.group(2)] = int(m.group(1))
            continue
        m = JEST.match(line)
        if m:
            c = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "xfailed": 0, "xpassed": 0, "rerun": 0, "deselected": 0}
            for n, w in re.findall(r"(\d+) (passed|failed|skipped|todo|pending)", m.group(1)):
                c["skipped" if w in ("todo", "pending") else w] += int(n)
            summary, framework = c, "jest"
    if summary is None and mocha:
        summary = {"passed": mocha.get("passing", 0), "failed": mocha.get("failing", 0), "skipped": mocha.get("pending", 0),
                   "errors": 0, "xfailed": 0, "xpassed": 0, "rerun": 0, "deselected": 0}
        framework = "mocha"
    return {"summary": summary, "framework": framework, "outcomes": outcomes}
