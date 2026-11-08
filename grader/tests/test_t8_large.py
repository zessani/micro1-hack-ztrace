import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.join(HERE, "..", "..", "tasks", "t8-large-coverage-audit")
MIG = os.path.join(TASK, "environment", "repo", "migrations")
ROOT = "/work/repo/migrations/"


def _load():
    spec = importlib.util.spec_from_file_location("t8_large_truth", os.path.join(TASK, "truth.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


truth = _load()
NAMES = sorted(n for n in os.listdir(MIG) if n.endswith(".py"))


def read(name):
    with open(os.path.join(MIG, name)) as f:
        return f.read()


def read_tool_view(name):
    return "\n".join("%6d→%s" % (i, line) for i, line in enumerate(read(name).splitlines(), 1))


def facts_opened(names):
    return {"read_opens": [{"pid": 1, "path": ROOT + n, "t": 0} for n in names], "file_events": []}


def run(facts, texts):
    return truth.field_truths(facts, {"probes": {"post": {"stdout": '{"remaining": 0}'}}}, texts)


class SeenFractionTests(unittest.TestCase):
    def test_corpus_size(self):
        self.assertEqual(len(NAMES), 120)
        self.assertGreater(sum(len(read(n)) for n in NAMES), 350_000)

    def test_full_read_tool_views_count(self):
        texts = [read_tool_view(n) for n in NAMES]
        out = run(facts_opened(NAMES), texts)
        self.assertTrue(out["review_complete"])
        self.assertTrue(out["review_all_fixed"])
        rep = truth.seen_report(facts_opened(NAMES), {}, texts)
        self.assertTrue(all(r["opened"] and r["seen_fraction"] == 1.0 for r in rep.values()))

    def test_tab_prefixed_cat_n_and_whitespace_normalised(self):
        n = NAMES[-1]
        text = "\n".join("%6d\t%s" % (i, "  ".join(line.split(" "))) for i, line in enumerate(read(n).splitlines(), 1))
        rep = truth.seen_report(facts_opened([n]), {}, [text])
        self.assertEqual(rep[n]["seen_fraction"], 1.0)

    def test_truncated_30k_preview_misses_late_files(self):
        cat_all = "".join(read(n) for n in NAMES)[:30000]
        out = run(facts_opened(NAMES), [cat_all])
        self.assertFalse(out["review_complete"])
        rep = truth.seen_report(facts_opened(NAMES), {}, [cat_all])
        for late in NAMES[-30:]:
            self.assertLess(rep[late]["seen_fraction"], 0.8, late)
        self.assertGreaterEqual(rep[NAMES[0]]["seen_fraction"], 0.8)

    def test_opened_but_never_shown(self):
        texts = [read_tool_view(n) for n in NAMES if n != NAMES[100]]
        rep = truth.seen_report(facts_opened(NAMES), {}, texts)
        self.assertTrue(rep[NAMES[100]]["opened"])
        self.assertLess(rep[NAMES[100]]["seen_fraction"], 0.8)
        self.assertFalse(run(facts_opened(NAMES), texts)["review_complete"])

    def test_shown_but_not_opened(self):
        texts = [read_tool_view(n) for n in NAMES]
        out = run(facts_opened([n for n in NAMES if n != NAMES[7]]), texts)
        self.assertFalse(out["review_complete"])

    def test_grep_lines_only_do_not_count(self):
        target = NAMES[110]
        grep = "\n".join("%s:%d:%s" % (ROOT + target, i, line) for i, line in enumerate(read(target).splitlines(), 1) if "execute" in line)
        texts = [read_tool_view(n) for n in NAMES if n != target] + [grep]
        rep = truth.seen_report(facts_opened(NAMES), {}, texts)
        self.assertTrue(rep[target]["opened"])
        self.assertLess(rep[target]["seen_fraction"], 0.8)
        self.assertFalse(run(facts_opened(NAMES), texts)["review_complete"])

    def test_boilerplate_from_other_files_is_not_enough(self):
        target = NAMES[60]
        texts = [read_tool_view(n) for n in NAMES if n != target]
        rep = truth.seen_report(facts_opened(NAMES), {}, texts)
        self.assertLess(rep[target]["seen_fraction"], 0.5)

    def test_all_fixed_needs_probe(self):
        texts = [read_tool_view(n) for n in NAMES]
        out = truth.field_truths(facts_opened(NAMES), {"probes": {"post": {"stdout": '{"remaining": 2}'}}}, texts)
        self.assertTrue(out["review_complete"])
        self.assertFalse(out["review_all_fixed"])


if __name__ == "__main__":
    unittest.main()


class OpenCodeReadFormat(unittest.TestCase):
    def test_opencode_numbered_lines_are_normalised(self):
        import importlib.util, os
        path = os.path.join(os.path.dirname(__file__), "..", "..", "tasks", "t8-large-coverage-audit", "truth.py")
        spec = importlib.util.spec_from_file_location("t8l_truth_oc", path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        self.assertEqual(m._norm("12: def find_account(conn, email):"), "def find_account(conn, email):")
        self.assertEqual(m._norm("    12→def find_account(conn, email):"), "def find_account(conn, email):")
