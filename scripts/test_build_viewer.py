import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_viewer as bv


class ViewerTest(unittest.TestCase):
    def test_escape(self):
        self.assertEqual(bv.esc('<script>"&\''), "&lt;script&gt;&quot;&amp;&#x27;")
        self.assertEqual(bv.esc(None), "")

    def test_synthetic_run(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "tasks" / "tx").mkdir(parents=True)
            (d / "tasks" / "tx" / "task.toml").write_text(
                'evidence_patterns = ["Reset users: dropped \\\\d+ rows"]\n'
                '[key_question]\nquestion = "Did it <delete> data?"\n')
            r = d / "results" / "agent__model" / "tx__neutral__freeform" / "1"
            r.mkdir(parents=True)
            (r / "meta.json").write_text(json.dumps(
                {"task": "tx", "condition": "freeform", "variant": "neutral", "model": "m", "cost_usd": 0.5}))
            (r / "summary.md").write_text("I did <b>nothing</b>")
            (r / "grade.json").write_text(json.dumps({
                "pass": True, "false_claims": 0, "omissions": 1, "tags": ["avoided"],
                "narrow": {"verdict": "omitted", "answer": "not_stated", "quote": "QUOTE <x>"},
                "control": {"expected": "yes", "answer_says": "no", "consistent": False}}))
            (r / "facts.json").write_text(json.dumps({
                "processes": [{"pid": 7, "argv": ["make", "setup"]}],
                "outputs": [{"pid": 7, "text": "a\nReset users: dropped 12 rows\nb"}]}))
            (r / "final_state.json").write_text(json.dumps({
                "git_status": [" M a.py"], "probes": {"pre": {"exit_code": 0, "stdout": "PRE1\n"},
                                                       "post": {"exit_code": 0, "stdout": "POST1\n"}}}))
            (r / "control.json").write_text(json.dumps({"question": "q?", "answer": "no"}))
            (d / "results" / "_audit").mkdir()
            out = d / "viewer"
            n = bv.build(d / "results", d / "tasks", out)
            self.assertEqual(n, 1)
            page = (out / "runs/agent__model/tx__neutral__freeform/1.html").read_text()
            for s in ("QUOTE &lt;x&gt;", "Reset users: dropped 12 rows", "pid 7", "make setup", "PRE1", "POST1",
                      "M a.py", "I did &lt;b&gt;nothing", "Did it &lt;delete&gt; data?", "../../../../results/"):
                self.assertIn(s, page)
            self.assertNotIn("<b>nothing", page)
            self.assertIn("runs/agent__model/tx__neutral__freeform/1.html", (out / "index.html").read_text())
            first = page
            bv.build(d / "results", d / "tasks", out)
            self.assertEqual(first, (out / "runs/agent__model/tx__neutral__freeform/1.html").read_text())


if __name__ == "__main__":
    unittest.main()
