"""SVG charts in one shared theme (see theme.py)."""
from .core import MAIN_MODELS, HARD, TASK_ORDER
from .theme import (COLOR, SHORT, LABEL, TASK_NAME, ALL_C, SOME_C, NONE_C, W, PAD, LEFT, INK, MUTE, GRID, TRACK, S_LABEL, S_VALUE, S_AXIS,
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
    return _hbars("Hard-set pass rate (hard tasks only, 95% CI)", "", items, "Hard-set pass rate per model with Wilson 95% intervals")


def chart_important(d):
    """One bar per model: share of important events reported. d = numbers['derived']."""
    imp = d["important_events_reported"]
    items = sorted([(m, v) for m, v in imp.items() if v["n_events"]], key=lambda x: -x[1]["pct"])
    n_ev = sum(v["n_events"] for _, v in items)
    n_runs = sum(v["n_runs"] for _, v in items)
    left, x1 = 270, W - PAD - 90
    pw = x1 - left
    row, top = 50, 86
    H = top + row * len(items) + 16
    b = [title("Share of important events the agent reported in its PR summary"),
         t(PAD, PAD + 36, "Hard tasks, 95%% CI. %d events in %d runs." % (n_ev, n_runs), S_AXIS, fill=MUTE)]
    for i, (m, v) in enumerate(items):
        ye = top + row * i + row / 2
        b.append(t(left - 14, ye + 5, LABEL[m], S_LABEL, "end"))
        w = pw * v["pct"]
        b.append("<rect x='%d' y='%.1f' width='%.1f' height='26' rx='2' fill='%s'/>" % (left, ye - 13, max(w, 0), COLOR[m]))
        xl, xh = left + pw * v["ci_low"], left + pw * v["ci_high"]
        b.append("<g stroke='%s' stroke-width='1.5'><line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f'/>"
                 "<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f'/><line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f'/></g>"
                 % (INK, xl, ye, xh, ye, xl, ye - 6, xl, ye + 6, xh, ye - 6, xh, ye + 6))
        lab = "%d%%" % round(v["pct"] * 100)
        if w > 70:
            b.append(t(left + 10, ye + 5, lab, S_VALUE, fill="#fff", weight="700"))
        else:
            b.append(t(xh + 10, ye + 5, lab, S_VALUE, fill=INK, weight="700"))
    return svg(H, "".join(b), "Share of important events reported per model, with 95% intervals")


def chart_asked(d):
    """Of hard-task runs where the summary left an event out, the share where the agent confirmed it when asked."""
    a = d["asked_directly"]
    items = [(m, v["confirmed_when_asked"] / v["runs_with_missed_event"], None, None,
              "%d of %d" % (v["confirmed_when_asked"], v["runs_with_missed_event"]))
             for m, v in a.items() if v["runs_with_missed_event"]]
    items.sort(key=lambda x: -x[1])
    return _hbars("Reported only when asked directly (hard tasks, runs with a missed event)", "", items,
                  "Share of runs with a missed event where the agent confirmed it when asked directly")


def chart_grid(d):
    """Rows: hard tasks. Columns: models. Cell: runs where every important event was reported / runs with one."""
    te = d["task_events"]
    models = [m for m in COLOR if m in te]
    tasks = [x for x in TASK_NAME if any(x in te[m] for m in models)]
    x0, cw, ch, top = 270, (W - PAD - 270) / len(models), 46, 100
    H = top + ch * len(tasks) + PAD
    b = [title("Important events reported, per task and model"),
         t(PAD, PAD + 36, "Runs where every important event was reported / runs with an important event. Hard tasks.", S_AXIS, fill=MUTE)]
    for i, m in enumerate(models):
        b.append(t(x0 + cw * i + cw / 2, top - 12, SHORT[m], S_AXIS, "middle", INK, "600"))
    for j, tk in enumerate(tasks):
        y = top + ch * j
        b.append(t(x0 - 14, y + ch / 2 + 5, TASK_NAME[tk], S_LABEL, "end"))
        for i, m in enumerate(models):
            c = te[m].get(tk)
            x = x0 + cw * i
            if not c:
                fill, txt, col = "#fff", "not run", MUTE
            elif not c["runs_with_events"]:
                fill, txt, col = "#fff", "no event", MUTE
            else:
                k, n = c["runs_all_reported"], c["runs_with_events"]
                fill = ALL_C if k == n else NONE_C if k == 0 else SOME_C
                txt, col = "%d / %d" % (k, n), ("#fff" if fill == ALL_C else INK)
            b.append("<rect x='%.1f' y='%d' width='%.1f' height='%d' fill='%s' stroke='%s' stroke-width='3'/>"
                     % (x, y, cw, ch, fill, "#fff" if fill != "#fff" else TRACK))
            b.append(t(x + cw / 2, y + ch / 2 + 5, txt, S_LABEL, "middle", col, "600"))
    ly = H - 10
    for k, (c, lab) in enumerate(((ALL_C, "all reported"), (SOME_C, "some"), (NONE_C, "none"))):
        lx = x0 + 150 * k
        b.append("<rect x='%d' y='%d' width='14' height='14' fill='%s'/>" % (lx, ly - 12, c))
        b.append(t(lx + 22, ly, lab, S_AXIS, fill=MUTE))
    return svg(H + 20, "".join(b), "Per-task grid of important events reported")


AROW = 64


def chart_audit(rows_agg):
    models = [m for m in MAIN_MODELS if m in rows_agg and rows_agg[m]["claim_accuracy"] is not None
              and rows_agg[m]["disclosure_rate_all_events"] is not None]
    x0, x1 = LEFT, W - PAD - 30
    pw = x1 - x0
    H = TOP + 20 + AROW * len(models) + 40
    b = [title("Claim accuracy and disclosure (all tasks, main runs)")]
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
