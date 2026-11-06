import subprocess
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def pytest_sessionstart(session):
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "codegen.py")],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(out)
    else:
        sys.stderr.write(out + "\n")
