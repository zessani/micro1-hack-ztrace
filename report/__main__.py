"""python3 -m report: build report/out/index.html, report/img/*.svg|png, report/numbers.json."""
import json
import shutil
import subprocess
from pathlib import Path

from . import charts, core, render

HERE = Path(__file__).resolve().parent


def svg_to_png(svg, png):
    """rsvg-convert at 2x width; fall back to sips. Returns the tool used or None."""
    exe = shutil.which("rsvg-convert")
    if exe:
        subprocess.run([exe, "-w", "1520", "-o", str(png), str(svg)], check=True)
        return "rsvg-convert"
    exe = shutil.which("sips")
    if exe:
        subprocess.run([exe, "-s", "format", "png", str(svg), "--out", str(png)],
                       check=True, capture_output=True)
        return "sips"
    return None


def main():
    runs, skipped = core.load_runs()
    agg = core.aggregate(runs)
    out, img = HERE / "out", HERE / "img"
    out.mkdir(exist_ok=True)
    img.mkdir(exist_ok=True)
    svgs = {"pass_rate": charts.chart_pass_rate(agg), "grid": charts.chart_grid(agg),
            "knew_but_didnt_say": charts.chart_kbds(agg)}
    tool = None
    for name, svg in svgs.items():
        (img / (name + ".svg")).write_text(svg)
        tool = svg_to_png(img / (name + ".svg"), img / (name + ".png")) or tool
    (out / "index.html").write_text(render.page(agg, runs, skipped, list(svgs.values())))
    numbers = {"groups": agg, "skipped": skipped, "n_runs": len(runs), "wilson_z": 1.96,
               "pass_rate_denominator": "scored runs (avoided/not_run excluded)"}
    (HERE / "numbers.json").write_text(json.dumps(numbers, indent=1, sort_keys=True) + "\n")
    size = (out / "index.html").stat().st_size
    print("runs=%d skipped=%s html=%d bytes png_tool=%s" % (len(runs), skipped, size, tool))


if __name__ == "__main__":
    main()
