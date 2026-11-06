"""Version parsing and ordering."""
import re

_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


class Version:
    def __init__(self, text):
        m = _PATTERN.match(text.strip())
        if not m:
            raise ValueError("invalid version: %r" % text)
        self.text = "%s.%s.%s" % m.groups()
        self.parts = tuple(int(p) for p in m.groups())

    def __str__(self):
        return self.text


def compare_versions(a, b):
    """Return -1, 0 or 1 if a is lower than, equal to or higher than b."""
    pa, pb = str(Version(a)), str(Version(b))
    if pa == pb:
        return 0
    return -1 if pa < pb else 1


def latest(versions):
    best = None
    for v in versions:
        if best is None or compare_versions(v, best) > 0:
            best = v
    return best
