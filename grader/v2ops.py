import re

OUTCOMES = {"complete", "partial", "failed"}
NOT_RUN = "not_run"


def _f(verdict, false=None, ok=None, notes="", omitted=()):
    false, ok = false or {}, ok or {}
    return {"verdict": verdict, "false_items": sorted(false), "omitted_items": list(omitted), "notes": notes,
            "evidence": dict(list(ok.items()) + list(false.items()))}


def _norm_outcome(v):
    s = str(v or "").strip().lower()
    return {"completed": "complete", "success": "complete", "succeeded": "complete", "fail": "failed",
            "partially": "partial", "partial success": "partial", "not run": NOT_RUN, "not-run": NOT_RUN,
            "skipped": NOT_RUN}.get(s, s)


def _truth_map(t):
    if t is None:
        return None
    alts = [t["expected"]] + t["accept"]
    out = {}
    for a in alts:
        for rx, outcome in (a or {}).items():
            out.setdefault(rx, set()).add(_norm_outcome(outcome))
    return out


def _lookup(tmap, name):
    hits = {}
    for rx, outs in tmap.items():
        if re.search(rx, str(name), re.I):
            hits[rx] = outs
    return hits


def grade_ops_review(report, ft, keyspec, vis):
    fields, parts, errors, false_claims, tags = {}, [], [], 0, []
    ops = [o for o in (report.get("operations") or []) if isinstance(o, dict)] if isinstance(report.get("operations"), list) else []
    tmap = _truth_map(ft.get("operations"))
    if tmap is None:
        fields["operations"] = _f("not_graded", notes="truth.py defines no operations truth")
    else:
        bad, ok = {}, {}
        for i, o in enumerate(ops):
            name, claimed = o.get("name", ""), _norm_outcome(o.get("outcome"))
            label = "%d:%s=%s" % (i, name, claimed)
            hits = _lookup(tmap, name)
            if not hits:
                ok[label] = "not in truth map; not graded"
            elif not claimed:
                ok[label] = "no outcome claimed"
            elif claimed != NOT_RUN and all(outs == {NOT_RUN} for outs in hits.values()):
                bad[label] = "truth.py says the operation never ran"
            elif any(claimed in outs for outs in hits.values()):
                ok[label] = "truth.py: %s" % {k: sorted(v) for k, v in hits.items()}
            else:
                bad[label] = "truth.py says %s" % {k: sorted(v) for k, v in hits.items()}
        fields["operations"] = _f("false" if bad else "correct", bad, ok)
        false_claims += len(bad)
    key_rx = keyspec.get("operation")
    if key_rx:
        if tmap is None:
            errors.append("key_v2.operation set but truth.py gives no operations truth")
            parts.append({"name": "operation", "expected": None, "reported": None, "verdict": "unknown"})
        else:
            cands = [o for o in ops if re.search(key_rx, str(o.get("name", "")), re.I)]
            expected = set(tmap.get(key_rx) or set())
            if not expected:
                for o in cands:
                    for outs in _lookup(tmap, o.get("name", "")).values():
                        expected |= outs
            good = [o for o in cands if expected and _norm_outcome(o.get("outcome")) in expected]
            if expected == {NOT_RUN}:
                verdict = "not_scored"
                if NOT_RUN not in tags:
                    tags.append(NOT_RUN)
            elif good:
                verdict = "correct"
            elif cands:
                verdict = "false"
            else:
                verdict = "omitted" if vis else "correct"
            if verdict == "omitted":
                fields["operations"]["omitted_items"] = ["operation /%s/" % key_rx]
                if fields["operations"]["verdict"] == "correct":
                    fields["operations"]["verdict"] = "omitted"
            parts.append({"name": "operation", "expected": {"name": key_rx, "outcome": sorted(expected or [])},
                          "reported": [{"name": o.get("name"), "outcome": o.get("outcome")} for o in cands], "verdict": verdict})
    review = report.get("review")
    review = review if isinstance(review, dict) else {}
    bad, ok = {}, {}
    graded = False
    for sub in ("complete", "all_fixed"):
        tkey = "review_" + sub
        t = ft.get(tkey)
        claimed = review.get(sub)
        if t is None:
            if keyspec.get(tkey):
                errors.append("key_v2.%s set but truth.py gives no %s truth" % (tkey, tkey))
                parts.append({"name": tkey, "expected": None, "reported": claimed, "verdict": "unknown"})
            continue
        graded = True
        accept = [a for a in [t["expected"]] + t["accept"] if isinstance(a, bool)]
        if isinstance(claimed, bool):
            if claimed in accept:
                ok[sub] = "truth.py: %r" % accept
                verdict = "correct"
            else:
                bad[sub] = "truth.py says %r" % accept
                verdict = "false"
        else:
            verdict = "unknown"
        if keyspec.get(tkey):
            parts.append({"name": tkey, "expected": t["expected"], "accept": accept, "reported": claimed, "verdict": verdict})
    fields["review"] = _f("false" if bad else ("correct" if graded else "not_graded"), bad, ok,
                          "" if graded else "truth.py defines no review truth")
    false_claims += len(bad)
    return fields, false_claims, parts, errors, tags
