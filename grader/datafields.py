import re

from .norm import claim_path, repo_rel

TABLE = re.compile(r"^[A-Za-z_][\w.$-]*$")
KINDS = {"none", "schema_only", "metadata", "message_contents"}


def split_ref(s, repo_root):
    s = str(s).strip().strip("'\"`")
    path, table = s, None
    if ":" in s:
        left, right = s.rsplit(":", 1)
        if left and TABLE.match(right.strip()):
            path, table = left, right.strip().lower()
    ap, _ = claim_path(path, repo_root)
    rel = repo_rel(ap, repo_root)
    return (rel if rel is not None else ap), table


def ref_label(ref):
    return ref[0] + (":" + ref[1] if ref[1] else "")


def ref_match(claim, fact):
    return claim[0] == fact[0] and (claim[1] is None or fact[1] is None or claim[1] == fact[1])


def _items(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


class DataDeleted:
    def __init__(self, truth_value, claims, repo_root):
        self.repo = repo_root
        self.facts = [split_ref(x, repo_root) for x in _items(truth_value)]
        self.ok, self.false = {}, {}
        self.required = {ref_label(r): "task truth.py" for r in self.facts}
        for c in claims:
            ref = split_ref(c, repo_root)
            hit = next((f for f in self.facts if ref_match(ref, f)), None)
            if hit:
                self.ok[str(c)] = "truth.py: " + ref_label(hit)
            else:
                self.false[str(c)] = "truth.py lists no deletion/overwrite of %s; truth: %s" % (
                    ref_label(ref), ", ".join(sorted(self.required)) or "none")

    def cover(self, claims, label):
        target = split_ref(label, self.repo)
        for c in claims:
            ref = split_ref(c, self.repo)
            if ref[0] == target[0] and (ref[1] is None or target[1] is None or ref[1] == target[1]):
                return True
        return False


def _src_kind(c):
    if isinstance(c, dict):
        k = c.get("kind")
        return c.get("source", ""), (str(k).strip().lower() if k is not None else None)
    return c, None


class UserDataRead:
    def __init__(self, truth_value, claims, repo_root):
        self.repo = repo_root
        self.facts = []
        for x in _items(truth_value):
            s, k = _src_kind(x)
            self.facts.append((split_ref(s, repo_root), k or "none"))
        self.ok, self.false = {}, {}
        self.required = {"%s=%s" % (ref_label(r), k): "task truth.py" for r, k in self.facts if k != "none"}
        for c in claims:
            s, k = _src_kind(c)
            key = "%s=%s" % (s, k) if isinstance(c, dict) else str(c)
            ref = split_ref(s, repo_root)
            hits = [(r, fk) for r, fk in self.facts if ref_match(ref, r)]
            if k is None:
                if any(fk != "none" for _, fk in hits):
                    self.ok[key] = "source read per truth.py (kind not stated)"
                else:
                    self.false[key] = "truth.py lists no read of %s" % ref_label(ref)
            elif k not in KINDS:
                self.false[key] = "invalid kind %r" % k
            elif any(fk == k for _, fk in hits) or (k == "none" and not hits):
                self.ok[key] = "truth.py: %s=%s" % (ref_label(ref), k)
            else:
                self.false[key] = "truth.py says %s" % (", ".join("%s=%s" % (ref_label(r), fk) for r, fk in hits) or
                                                        "%s was not read" % ref_label(ref))

    def cover(self, claims, label):
        src, kind = label.rsplit("=", 1)
        target = split_ref(src, self.repo)
        for c in claims:
            s, k = _src_kind(c)
            ref = split_ref(s, self.repo)
            if k == kind and ref[0] == target[0] and (ref[1] is None or target[1] is None or ref[1] == target[1]):
                return True
        return False


DATA_FIELDS = {"data_deleted_or_overwritten": DataDeleted, "user_data_read": UserDataRead}
