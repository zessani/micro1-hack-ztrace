import unittest

from extractor.extract import verify

SUMMARY = """Fixed the falsy-value bug in `kvcache/redis_cache.py`.

**Testing:** ran `pytest`: 44 passed, 3 skipped. The Redis tests were skipped because no server is running, so the fix is not verified by the suite.
"""


def raw(**kw):
    base = {"changes": [], "testing": [], "verified_by_tests": {"value": None, "quote": ""}, "side_effects": [],
            "operations": [], "review": None, "summary": "Fixed it."}
    base.update(kw)
    return base


class QuoteChecks(unittest.TestCase):
    def test_supported_claims_kept_across_markdown(self):
        rep, dropped = verify(raw(
            changes=[{"path": "kvcache/redis_cache.py", "quote": "Fixed the falsy-value bug in kvcache/redis_cache.py"}],
            testing=[{"command": "pytest", "outcome": "passed", "passed": 44, "skipped": 3,
                      "quote": "ran pytest: 44 passed, 3 skipped"}],
            verified_by_tests={"value": False, "quote": "so the fix is not verified by the suite"}), SUMMARY)
        self.assertEqual(rep["changes"], ["kvcache/redis_cache.py"])
        self.assertEqual(rep["testing"][0]["passed"], 44)
        self.assertIs(rep["verified_by_tests"], False)
        self.assertEqual(dropped, [])

    def test_made_up_claim_dropped(self):
        rep, dropped = verify(raw(
            side_effects=[{"type": "network", "detail": "fetched schema", "quote": "the setup script fetched a remote schema file"}],
            verified_by_tests={"value": True, "quote": "all tests pass and the fix is verified"}), SUMMARY)
        self.assertEqual(rep["side_effects"], [])
        self.assertIsNone(rep["verified_by_tests"])
        self.assertEqual({d["field"] for d in dropped}, {"side_effects", "verified_by_tests"})

    def test_short_fragment_dropped(self):
        rep, dropped = verify(raw(verified_by_tests={"value": True, "quote": "44 passed"}), SUMMARY)
        self.assertIsNone(rep["verified_by_tests"])
        self.assertEqual(len(dropped), 1)

    def test_short_full_sentence_kept(self):
        rep, _ = verify(raw(changes=[{"path": "a.py", "quote": "Done."}]), "Updated a.py for the reviewer today.\nDone.")
        self.assertEqual(rep["changes"], ["a.py"])

    def test_not_mentioned_is_null_not_false(self):
        rep, dropped = verify(raw(), SUMMARY)
        self.assertIsNone(rep["verified_by_tests"])
        self.assertIsNone(rep["review"])
        self.assertEqual(dropped, [])

    def test_missing_quote_dropped(self):
        rep, dropped = verify(raw(changes=[{"path": "x.py"}]), SUMMARY)
        self.assertEqual(rep["changes"], [])
        self.assertEqual(len(dropped), 1)

    def test_smart_quotes_and_case(self):
        s = "We didn’t touch the database; nothing was deleted from it."
        rep, _ = verify(raw(side_effects=[{"type": "other", "detail": "x", "quote": "we didn't touch the database"}]), s)
        self.assertEqual(len(rep["side_effects"]), 1)


if __name__ == "__main__":
    unittest.main()
