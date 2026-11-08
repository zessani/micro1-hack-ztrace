"""SVG charts in one shared theme (see theme.py)."""
from .core import MAIN_MODELS, HARD, TASK_ORDER
from .theme import (COLOR, SHORT, W, PAD, LEFT, INK, MUTE, GRID, TRACK, S_LABEL, S_VALUE, S_AXIS,
                    t, svg, title, pct_axis, hline)

ROW = 52
TOP = 72


def _models(agg):
    return agg.get("main", {}).get("models", {})


def _hbars(name, label, items, aria):
    """items: (model, value, lo, hi, text). Horizontal bars on a 0-100% axis, label at the bar end."""
    x0, x1 = LEFT, W - PAD - 60
    pw = x1 - x0
    H = TOP + ROW * len(items) + 40
    b = [title(name)]
    for i, (m, v, lo, hi, text) in enumerate(items):
        y = TOP + ROW * i
        b.append(hline(PAD, W - PAD, y + ROW))
        b.append(t(LEFT - 14, y + ROW / 2 + 5, SHORT[m], S_LABEL, "end"))
        ye = y + ROW / 2
        b.append("<rect x='%d' y='%.1f' width='%.1f' height='24' rx='2' fill='%s'/>"
                 % (x0, ye - 12, max(pw * v, 0), COLOR[m]))
        end = x0 + pw * v
        if lo is not None:
            xl, xh = x0 + pw * lo, x0 + pw * hi
            b.append("<g stroke='%s' stroke-width='1.5'><line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f'/>"
                     "<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f'/><line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f'/></g>"
                     % (INK, xl, ye, xh, ye, xl, ye - 6, xl, ye + 6, xh, ye - 6, xh, ye + 6))
            end = max(end, xh)
        b.append(t(end + 8, ye + 5, text, S_VALUE, fill=INK, weight="600"))
    b.append(pct_axis(x0, x1, TOP + ROW * len(items) + 24))
    return svg(H, "".join(b), aria)


def chart_hard(agg):
    ms = _models(agg)
    items = []
    for m in MAIN_MODELS:
        o = ms.get(m, {}).get("by_set", {}).get("hard")
        if o and o["n"]:
            items.append((m, o["pass_rate"], o["ci_low"], o["ci_high"], "%d/%d" % (o["passes"], o["n"])))
    return _hbars("Hard-set pass rate", "", items, "Hard-set pass rate per model with Wilson 95% intervals")


def chart_kbds(agg):
    ms = _models(agg)
    items = []
    for m in MAIN_MODELS:
        o = ms.get(m, {}).get("overall")
        if o and o["runs_with_control"]:
            k, n = o["knew_but_didnt_say"], o["runs_with_control"]
            items.append((m, k / n, None, None, "%d/%d" % (k, n)))
    return _hbars("Disclosed only when asked", "", items,
                  "Share of runs where the summary missed the fact but the control answer stated it")


def _short_task(tk):
    return "t8-large" if "large" in tk else tk.split("-")[0]


def _shade(rate):
    a, c = (232, 240, 252), (23, 60, 130)
    return "#%02x%02x%02x" % tuple(round(a[k] + (c[k] - a[k]) * rate) for k in range(3)), rate > 0.55


def chart_grid(agg):
    ms = _models(agg)
    tasks = [x for x in TASK_ORDER if x in HARD and any(x in md["tasks"] for md in ms.values())]
    models = [m for m in MAIN_MODELS if m in ms and any(x in ms[m]["tasks"] for x in tasks)]
    x0 = LEFT
    cw = (W - PAD - x0) / len(tasks)
    ch = 50
    top = TOP + 18
    H = top + ch * len(models) + PAD
    b = [title("Pass rate by task")]
    for i, tk in enumerate(tasks):
        b.append(t(x0 + cw * i + cw / 2, top - 12, _short_task(tk), S_LABEL, "middle", MUTE))
    for j, m in enumerate(models):
        y = top + ch * j
        b.append(t(LEFT - 14, y + ch / 2 + 5, SHORT[m], S_LABEL, "end"))
        for i, tk in enumerate(tasks):
            c = ms[m]["tasks"].get(tk)
            x = x0 + cw * i
            if not c or not c["n"]:
                fill, txt, white = TRACK, "–", False
            else:
                fill, white = _shade(c["pass_rate"])
                txt = "%d/%d" % (c["passes"], c["n"])
            b.append("<rect x='%.1f' y='%d' width='%.1f' height='%d' fill='%s' stroke='#fff' stroke-width='3'/>"
                     % (x, y, cw, ch, fill))
            b.append(t(x + cw / 2, y + ch / 2 + 5, txt, S_LABEL, "middle", "#fff" if white else (MUTE if fill == TRACK else INK), "600"))
    return svg(H, "".join(b), "Pass counts per model and hard-set task")


AROW = 64


def chart_audit(rows_agg):
    models = [m for m in MAIN_MODELS if m in rows_agg and rows_agg[m]["claim_accuracy"] is not None
              and rows_agg[m]["disclosure_rate_all_events"] is not None]
    x0, x1 = LEFT, W - PAD - 30
    pw = x1 - x0
    H = TOP + 20 + AROW * len(models) + 40
    b = [title("Claim accuracy and disclosure")]
    ly = PAD + 14
    lx = W - PAD - 290
    b.append("<circle cx='%d' cy='%d' r='6' fill='%s'/>" % (lx, ly - 5, MUTE))
    b.append(t(lx + 12, ly, "Claim accuracy", S_AXIS, fill=MUTE))
    b.append("<circle cx='%d' cy='%d' r='5' fill='#fff' stroke='%s' stroke-width='2.5'/>" % (lx + 132, ly - 5, MUTE))
    b.append(t(lx + 144, ly, "Material disclosure", S_AXIS, fill=MUTE))
    top = TOP + 20
    for i, m in enumerate(models):
        a = rows_agg[m]
        acc, dis = a["claim_accuracy"], a["disclosure_rate_all_events"]
        y = top + AROW * i
        yc = y + AROW / 2
        b.append(hline(PAD, W - PAD, y + AROW))
        b.append(t(LEFT - 14, yc + 5, SHORT[m], S_LABEL, "end"))
        xa, xd = x0 + pw * acc, x0 + pw * dis
        col = COLOR[m]
        b.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='%s' stroke-width='4' stroke-opacity='0.35'/>"
                 % (xa, yc, xd, yc, col))
        b.append("<circle cx='%.1f' cy='%.1f' r='8' fill='%s'/>" % (xa, yc, col))
        b.append("<circle cx='%.1f' cy='%.1f' r='7' fill='#fff' stroke='%s' stroke-width='3'/>" % (xd, yc, col))
        hi = max(xa, xd)
        if abs(xa - xd) < 60:
            b.append(t(xa, yc - 15, "%d%%" % round(acc * 100), S_VALUE, "middle", INK, "600"))
            b.append(t(xd, yc + 26, "%d%%" % round(dis * 100), S_VALUE, "middle", INK, "600"))
            continue
        for xv, v in ((xa, acc), (xd, dis)):
            if xv == hi:
                b.append(t(xv + 14, yc + 5, "%d%%" % round(v * 100), S_VALUE, fill=INK, weight="600"))
            elif xv - x0 < 50:
                b.append(t(xv, yc - 14, "%d%%" % round(v * 100), S_VALUE, "middle", INK, "600"))
            else:
                b.append(t(xv - 14, yc + 5, "%d%%" % round(v * 100), S_VALUE, "end", INK, "600"))
    b.append(pct_axis(x0, x1, top + AROW * len(models) + 24))
    return svg(H, "".join(b), "Claim accuracy and material disclosure rate per model")
