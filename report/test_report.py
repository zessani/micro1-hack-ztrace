import unittest

from report import core


class WilsonTest(unittest.TestCase):
    def test_known_values(self):
        lo, hi = core.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=3)
        self.assertAlmostEqual(hi, 0.7634, places=3)
        lo, hi = core.wilson(0, 5)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.4345, places=3)
        lo, hi = core.wilson(5, 5)
        self.assertAlmostEqual(lo, 0.5655, places=3)
        self.assertEqual(hi, 1.0)

    def test_empty(self):
        self.assertIsNone(core.wilson(0, 0))


class GroupingTest(unittest.TestCase):
    def test_parse_label(self):
        self.assertEqual(core.parse_label("t1-x"), ("t1-x", None, False))
        self.assertEqual(core.parse_label("t5-x__neutral__freeform"), ("t5-x", "neutral", True))
        self.assertEqual(core.parse_label("t8-x__neutral-ticketv1__freeform"),
                         ("t8-x", "neutral-ticketv1", True))
        self.assertEqual(core.parse_label("t7-x__pressure"), ("t7-x", "pressure", False))

    def test_groups(self):
        c = core.classify
        sonnet, opus = "claude-code__claude-sonnet-5-5", core.OPUS
        self.assertEqual(c(sonnet, "t5-test-wipes-dev-db", "neutral", "freeform", 1), core.MAIN)
        self.assertEqual(c(opus, "t1-typeorm-vacuous", None, "structured", 2), core.PILOT)
        self.assertNotEqual(c(opus, "t1-typeorm-vacuous", None, "structured", 4), core.PILOT)
        self.assertNotEqual(c(opus, "t5-test-wipes-dev-db", None, "structured", 1), core.PILOT)
        self.assertEqual(c(opus, "t7-message-snapshot-read", "pressure", "freeform", 1),
                         "side:freeform/pressure")
        self.assertEqual(c(opus, "t8-coverage-audit", "neutral", "structured", 1),
                         "side:structured/neutral")
        self.assertEqual(c(sonnet, "t8-coverage-audit", "neutral-ticketv1", "freeform", 1),
                         "side:freeform/neutral-ticketv1")
        self.assertEqual(c("other__model", "t1", "neutral", "freeform", 1), "side:freeform/neutral")


class MetricsTest(unittest.TestCase):
    def test_avoided_excluded(self):
        base = {"scored": True, "pass": True, "false_claims": 0, "omissions": 0,
                "kbds": False, "has_control": False, "tags": [], "cost": 1.0}
        runs = [dict(base), {**base, "pass": False, "false_claims": 2},
                {**base, "scored": False, "tags": ["avoided"]}]
        m = core.metrics(runs)
        self.assertEqual((m["n"], m["passes"], m["avoided_not_scored"]), (2, 1, 1))
        self.assertEqual((m["false_claims"], m["runs_with_false_claim"]), (2, 1))
        self.assertEqual(m["cost_total_usd"], 3.0)


if __name__ == "__main__":
    unittest.main()
