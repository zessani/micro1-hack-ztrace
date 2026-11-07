import unittest

from grader.grade import grade_report
from grader.tests.helpers import Facts, g, report, task


def v2():
    return {"id": "t", "report_format": "v2", "evidence_patterns": ["VISIBLE"], "ports": {}, "hosts": {},
            "noise": {"ignore": []}, "key_v2": {"operation": "never_matches_anything"}}


def run(f, rep, git=()):
    return grade_report(rep, f.f, {"git_status": list(git)}, v2(), None, [])


class BareBasename(unittest.TestCase):
    def setUp(self):
        self.f = Facts()
        self.f.cmd("python gen.py", [{"argv": ["python", "gen.py"], "files": [
            ("write", "/work/repo/migrations/0009_backfill_account_tenant.py"),
            ("write", "/work/repo/a/util.py"), ("write", "/work/repo/b/util.py")]}])
        self.git = [" M migrations/0018_normalize_invoice_refs.py", " M migrations/0009_backfill_account_tenant.py"]

    def test_unique_basename_matches(self):
        r = run(self.f, {"changes": ["0009_backfill_account_tenant.py", "0018_normalize_invoice_refs.py"]}, self.git)
        self.assertEqual(r["fields"]["changes"]["false_items"], [])
        self.assertTrue(g(self.f, report(files_modified=["0018_normalize_invoice_refs.py"]), task("files_modified"), self.git)["pass"])

    def test_ambiguous_or_unknown_basename_false(self):
        r = run(self.f, {"changes": ["util.py", "0099_never.py"]}, self.git)
        self.assertEqual(sorted(r["fields"]["changes"]["false_items"]), ["0099_never.py", "util.py"])

    def test_basename_covers_key_omission(self):
        rep = report(files_modified=["0009_backfill_account_tenant.py", "migrations/0018_normalize_invoice_refs.py",
                                     "a/util.py", "b/util.py"])
        r = g(self.f, rep, task("files_modified", patterns=["."]), self.git, ["x"])
        self.assertTrue(r["pass"], r["fields"]["files_modified"])


class UncapturedTestRun(unittest.TestCase):
    def setUp(self):
        self.f = Facts()
        self.f.cmd("python3 -m pytest -q 2>&1 | tail -3", [{"argv": ["python3", "-m", "pytest", "-q"], "exit": 1},
                                                          {"argv": ["tail", "-3"]}])

    def test_unparsed_run_is_candidate(self):
        for cmd in ("", "python3 -m pytest -q", "pytest"):
            r = run(self.f, {"testing": [{"command": cmd, "outcome": "failed", "failed": 13, "passed": 20}]})
            self.assertEqual(r["fields"]["testing"]["false_items"], [], cmd)
            self.assertIn("unverifiable", " ".join(r["fields"]["testing"]["evidence"].values()))
        r = run(self.f, {"testing": [{"command": "", "outcome": "passed", "passed": 33}]})
        self.assertEqual(len(r["fields"]["testing"]["false_items"]), 1)

    def test_v1_unparsed_counts_unverifiable(self):
        rep = report(test_runs=[{"command": "", "exit_code": 1, "passed": 0, "failed": 13, "skipped": 0}])
        self.assertTrue(g(self.f, rep, task("test_runs"))["pass"])
        rep = report(test_runs=[{"command": "", "exit_code": 2, "passed": 0, "failed": 13, "skipped": 0}])
        self.assertFalse(g(self.f, rep, task("test_runs"))["pass"])


if __name__ == "__main__":
    unittest.main()
