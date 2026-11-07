import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "claude-haiku-5-5"
PROMPT = (HERE / "prompt.md").read_text()
KEYS = ("changes", "testing", "verified_by_tests", "side_effects", "summary")


def build_prompt(summary):
    return PROMPT.replace("{summary}", summary)


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    obj = json.loads(text[start:end + 1])
    return {k: obj.get(k, [] if k in ("changes", "testing", "side_effects") else None) for k in KEYS}


def extract(summary, docker_args):
    prompt = build_prompt(summary)
    cmd = docker_args + ["claude", "-p", prompt, "--model", MODEL, "--output-format", "json", "--max-turns", "1"]
    r = subprocess.run(cmd, text=True, capture_output=True, timeout=300)
    meta = {"model": MODEL, "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(), "exit_code": r.returncode}
    try:
        res = json.loads(r.stdout.strip().splitlines()[-1])
        meta.update({"cost_usd": res.get("total_cost_usd"), "raw": res.get("result", "")})
        return parse_json(res.get("result", "")), meta
    except (json.JSONDecodeError, IndexError, ValueError) as e:
        meta.update({"error": str(e), "raw": r.stdout[-4000:], "stderr": r.stderr[-2000:]})
        return None, meta


def main(argv=None):
    run_dir = Path((argv or sys.argv[1:])[0])
    print(build_prompt((run_dir / "summary.md").read_text()))


if __name__ == "__main__":
    main()
