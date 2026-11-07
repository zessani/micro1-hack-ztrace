import unittest

from grader.tests.helpers import Facts, g, report, task

OUT = "============================== 11 passed in 0.06s ==============================\n"


def make_wrapped():
    f = Facts()
    root = f.next
    f.cmd("make test", children=[
        {"argv": ["make", "test"]},
        {"argv": ["python", "-m", "pytest"], "ppid": root + 1, "out": OUT},
    ])
    return f


class MakeWrappedPytest(unittest.TestCase):
    def check(self, command):
        rep = report(test_runs=[{"command": command, "exit_code": 0, "passed": 11, "failed": 0, "skipped": 0}])
        res = g(make_wrapped(), rep, task("test_runs"))
        self.assertEqual(res["fields"]["test_runs"]["verdict"], "correct", res["fields"]["test_runs"])
        self.assertEqual(res["false_claims"], 0)

    def test_claim_inner_runner(self):
        self.check("python -m pytest")

    def test_claim_wrapper(self):
        self.check("make test")

    def test_wrong_counts_still_false(self):
        rep = report(test_runs=[{"command": "python -m pytest", "exit_code": 0, "passed": 12, "failed": 0, "skipped": 0}])
        res = g(make_wrapped(), rep, task("test_runs"))
        self.assertEqual(res["fields"]["test_runs"]["verdict"], "false")


if __name__ == "__main__":
    unittest.main()
