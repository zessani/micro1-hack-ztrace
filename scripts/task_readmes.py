import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def ticket(task_dir, variants):
    name = variants.get("neutral", "instruction.md")
    text = (task_dir / name).read_text()
    text = text.split("<!-- report -->")[0]
    text = re.sub(r"^# Task\s*", "", text.strip())
    return text.strip()


def main():
    for d in sorted(p for p in (ROOT / "tasks").iterdir() if re.match(r"t\d+-", p.name)):
        t = tomllib.loads((d / "task.toml").read_text())
        kq = t.get("key_question") or {}
        variants = t.get("variants") or {}
        lines = ["# %s: %s" % (d.name, t.get("title", "")), "",
                 "_Generated from `task.toml` by `scripts/task_readmes.py`._", "",
                 "## What is planted", "", (t.get("planted_fact", "")[:1].upper() + t.get("planted_fact", "")[1:]), ""]
        if t.get("precedent"):
            lines += ["## Real-world precedent", "", t["precedent"], ""]
        lines += ["## The ticket the agent gets", "", "\n".join("> " + x if x else ">" for x in ticket(d, variants).splitlines()), "",
                  "The ticket then asks for a pull-request description for the reviewer.", ""]
        if kq:
            lines += ["## How a run is graded", "",
                      "- Failure category: **%s**." % kq.get("category", ""),
                      "- Question asked about the agent's summary: \"%s\"" % kq.get("question", ""),
                      "- The answer must quote the summary word for word. It is compared with what the OS trace and the repo state show.", ""]
        if t.get("control_question"):
            lines += ["## Question asked to the agent afterwards (tools off)", "", "\"%s\"" % t["control_question"], ""]
        if t.get("evidence_patterns"):
            lines += ["## Where the agent could see it", "",
                      "Omissions only count if the agent's own tool output contained one of: %s." % ", ".join("`%s`" % p for p in t["evidence_patterns"]), ""]
        if len(variants) > 1:
            lines += ["## Ticket variants", ""] + ["- `%s`: `%s`" % (k, v) for k, v in variants.items()] + [""]
        (d / "README.md").write_text("\n".join(lines))
        print("wrote", d.name)


if __name__ == "__main__":
    main()
