"""python3 -m report: build report/out/index.html, report/img/*.svg|png, report/numbers.json."""
import json
import shutil
import subprocess
from pathlib import Path

from . import audit, charts, core, metrics, render

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
    rows, audit_agg = audit.run_audit(runs)
    audit.write_audit(rows, audit_agg)
    byp = {r["path"]: r for r in rows}
    for r in runs:
        r["audit"] = byp.get(r["path"])
    derived = metrics.compute(runs, audit_agg["main"])
    svgs = {"hard_pass_rate": charts.chart_hard(agg), "grid": charts.chart_grid(derived),
            "asked_directly": charts.chart_asked(derived), "important_events": charts.chart_important(derived)}
    audit_svg = charts.chart_audit(audit_agg["main"])
    svgs["audit"] = audit_svg
    tool = None
    for old in img.iterdir():
        if old.stem not in svgs:
            old.unlink()
    for name, svg in svgs.items():
        (img / (name + ".svg")).write_text(svg)
        tool = svg_to_png(img / (name + ".svg"), img / (name + ".png")) or tool
    (out / "index.html").write_text(render.page(agg, runs, skipped, svgs, audit_agg))
    numbers = {"groups": agg, "skipped": skipped, "n_runs": len(runs), "wilson_z": 1.96,
               "pass_rate_denominator": "scored runs (avoided/not_run excluded)",
               "audit": audit_agg["main"], "hard_set": core.hard_set(agg),
               "t8_ticket_comparison": core.ticket_comparison(runs), "derived": derived}
    (HERE / "numbers.json").write_text(json.dumps(numbers, indent=1, sort_keys=True) + "\n")
    size = (out / "index.html").stat().st_size
    print("runs=%d skipped=%s html=%d bytes png_tool=%s" % (len(runs), skipped, size, tool))


if __name__ == "__main__":
    main()
