"""Inline SVG charts, generated in Python (no JS)."""
from html import escape

from .core import MAIN_MODELS, HARD, TASK_ORDER

FONT = "font-family='Helvetica,Arial,sans-serif'"
INK, MUTE, GRID, BAR, ERR = "#1f2933", "#52606d", "#d9dee3", "#2f6f9f", "#102a43"
SHORT = {"claude-code__claude-opus-5-5": "Opus 5.5 (Claude Code)",
         "claude-code__claude-sonnet-5-5": "Sonnet 5.5 (Claude Code)",
         "opencode__meta_muse-spark-open": "Muse Spark Open (OpenCode)",
         "opencode__qwen_qwen3-coder": "Qwen3-Coder (OpenCode)"}


def _svg(w, h, body, title):
    return ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %d %d' width='%d' height='%d' "
            "role='img' aria-label='%s' %s><rect width='%d' height='%d' fill='#ffffff'/>%s</svg>"
            % (w, h, w, h, escape(title, quote=True), FONT, w, h, body))


def _t(x, y, s, size=12, anchor="start", fill=INK, weight="normal"):
    return ("<text x='%.1f' y='%.1f' font-size='%d' text-anchor='%s' fill='%s' font-weight='%s'>%s</text>"
            % (x, y, size, anchor, fill, weight, escape(str(s))))


def _pct(x):
    return "%d%%" % round(x * 100)


def chart_pass_rate(agg):
    """(a) pass rate per model with Wilson 95% bars, main matrix."""
    models = agg.get("main", {}).get("models", {})
    W, H, L, R, T = 760, 90 + 62 * len(MAIN_MODELS), 230, 40, 60
    pw = W - L - R
    b = [_t(W / 2, 26, "Pass rate per model, main matrix (Wilson 95% interval)", 15, "middle", weight="bold"),
         _t(W / 2, 44, "freeform, neutral; avoided runs excluded from n", 11, "middle", MUTE)]
    for i in range(6):
        x = L + pw * i / 5
        b.append("<line x1='%.1f' y1='%d' x2='%.1f' y2='%d' stroke='%s'/>" % (x, T - 6, x, H - 30, GRID))
        b.append(_t(x, H - 14, "%d%%" % (i * 20), 11, "middle", MUTE))
    for j, m in enumerate(MAIN_MODELS):
        y = T + 62 * j
        o = models.get(m, {}).get("overall")
        b.append(_t(L - 10, y + 22, SHORT[m], 12, "end"))
        if not o or not o["n"]:
            b.append(_t(L + 6, y + 22, "no scored runs", 12, fill=MUTE))
            continue
        x1 = L + pw * o["pass_rate"]
        b.append("<rect x='%d' y='%d' width='%.1f' height='26' fill='%s'/>" % (L, y + 8, x1 - L, BAR))
        lo, hi = L + pw * o["ci_low"], L + pw * o["ci_high"]
        yc = y + 21
        b.append("<g stroke='%s' stroke-width='2'><line x1='%.1f' y1='%d' x2='%.1f' y2='%d'/>"
                 "<line x1='%.1f' y1='%d' x2='%.1f' y2='%d'/><line x1='%.1f' y1='%d' x2='%.1f' y2='%d'/></g>"
                 % (ERR, lo, yc, hi, yc, lo, yc - 7, lo, yc + 7, hi, yc - 7, hi, yc + 7))
        b.append(_t(L + 4, y + 52, "%s  (%d/%d)  95%% CI %s-%s"
                    % (_pct(o["pass_rate"]), o["passes"], o["n"], _pct(o["ci_low"]), _pct(o["ci_high"])),
                    11, fill=MUTE))
    return _svg(W, H, "".join(b), "Pass rate per model with Wilson 95% intervals")


def _cell_color(rate):
    stops = [(0.0, (200, 80, 70)), (0.5, (236, 200, 110)), (1.0, (80, 160, 130))]
    for (a, ca), (c, cc) in zip(stops, stops[1:]):
        if rate <= c:
            f = (rate - a) / (c - a)
            return "#%02x%02x%02x" % tuple(round(ca[k] + (cc[k] - ca[k]) * f) for k in range(3))
    return "#50a082"


def chart_grid(agg):
    """(b) models x tasks grid coloured by pass rate; p/n plus F and O counts."""
    models = agg.get("main", {}).get("models", {})
    tasks = [t for t in TASK_ORDER if any(t in md["tasks"] for md in models.values())]
    cw, ch, L, T = 96, 64, 210, 185
    W, H = L + cw * len(tasks) + 60, T + ch * len(MAIN_MODELS) + 30
    b = [_t(W / 2, 26, "Models x tasks, main matrix", 15, "middle", weight="bold"),
         _t(W / 2, 44, "cell: pass/n, F = false claims, O = omissions; colour = pass rate", 11, "middle", MUTE)]
    for i, t in enumerate(tasks):
        x = L + cw * i + cw / 2
        tag = "hard" if t in HARD else "reliable"
        b.append("<g transform='translate(%.1f,%d) rotate(-35)'>%s</g>"
                 % (x - 20, T - 10, _t(0, 0, "%s (%s)" % (t, tag), 11)))
    for j, m in enumerate(MAIN_MODELS):
        y = T + ch * j
        b.append(_t(L - 10, y + ch / 2 + 4, SHORT[m], 12, "end"))
        for i, t in enumerate(tasks):
            x = L + cw * i
            c = models.get(m, {}).get("tasks", {}).get(t)
            if not c:
                fill, l1, l2 = "#eef0f2", "-", ""
            elif c["n"] == 0:
                fill, l1, l2 = "#eef0f2", "avoided", "x%d" % c["avoided_not_scored"]
            else:
                fill = _cell_color(c["pass_rate"])
                l1 = "%d/%d" % (c["passes"], c["n"])
                l2 = "F%d O%d" % (c["false_claims"], c["omissions"])
            b.append("<rect x='%d' y='%d' width='%d' height='%d' fill='%s' stroke='#fff' stroke-width='2'/>"
                     % (x, y, cw, ch, fill))
            b.append(_t(x + cw / 2, y + 28, l1, 15, "middle", weight="bold"))
            if l2:
                b.append(_t(x + cw / 2, y + 48, l2, 12, "middle"))
    return _svg(W, H, "".join(b), "Models by tasks grid of pass rates")


def chart_kbds(agg):
    """(c) knew but didn't say: control answer right, report missed or misstated the key fact."""
    models = agg.get("main", {}).get("models", {})
    W, H, L, R, T = 760, 90 + 50 * len(MAIN_MODELS), 230, 60, 70
    vals = [models.get(m, {}).get("overall", {}) for m in MAIN_MODELS]
    top = max([v.get("runs_with_control", 0) for v in vals] + [1])
    pw = W - L - R - 200
    b = [_t(W / 2, 26, "Knew but didn't say, main matrix", 15, "middle", weight="bold"),
         _t(W / 2, 44, "runs where the control answer stated the key fact but the report omitted or misstated it", 11, "middle", MUTE)]
    for j, m in enumerate(MAIN_MODELS):
        y = T + 50 * j
        v = vals[j]
        k, n = v.get("knew_but_didnt_say", 0), v.get("runs_with_control", 0)
        b.append(_t(L - 10, y + 20, SHORT[m], 12, "end"))
        b.append("<rect x='%d' y='%d' width='%.1f' height='24' fill='#eef0f2'/>" % (L, y + 4, max(pw * n / top, 1)))
        if k:
            b.append("<rect x='%d' y='%d' width='%.1f' height='24' fill='#c0504d'/>" % (L, y + 4, pw * k / top))
        b.append(_t(L + pw * n / top + 8, y + 21, "%d of %d runs with a control answer" % (k, n), 11, fill=MUTE))
    return _svg(W, H, "".join(b), "Knew but did not say per model")
