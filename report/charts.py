"""Inline SVG charts, generated in Python (no JS)."""
from html import escape

from .core import MAIN_MODELS, HARD, TASK_ORDER, OPUS, T8, TICKET_V1

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


def chart_hard(agg):
    """Headline: hard-set pass rate per model with Wilson 95% bars, main matrix."""
    models = agg.get("main", {}).get("models", {})
    W, H, L, R, T = 760, 130 + 62 * len(MAIN_MODELS), 230, 40, 60
    pw = W - L - R
    present = [t for t in HARD if any(t in md["tasks"] for md in models.values())]
    b = [_t(W / 2, 26, "Pass rate on the hard set, main matrix (Wilson 95% interval)", 15, "middle", weight="bold"),
         _t(W / 2, 44, "freeform, neutral; avoided runs excluded from n", 11, "middle", MUTE)]
    for i in range(6):
        x = L + pw * i / 5
        b.append("<line x1='%.1f' y1='%d' x2='%.1f' y2='%d' stroke='%s'/>" % (x, T - 6, x, H - 70, GRID))
        b.append(_t(x, H - 54, "%d%%" % (i * 20), 11, "middle", MUTE))
    for j, m in enumerate(MAIN_MODELS):
        y = T + 62 * j
        o = models.get(m, {}).get("by_set", {}).get("hard")
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
    b.append(_t(L, H - 34, "Hard set: " + ", ".join(present), 10, fill=MUTE))
    b.append(_t(L, H - 20, "Opus ran t8-coverage-audit with ticket v1 only.", 10, fill=MUTE))
    return _svg(W, H, "".join(b), "Hard-set pass rate per model with Wilson 95% intervals")


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
         _t(W / 2, 44, "cell: pass/n, F = key fact misstated, O = key fact not stated; colour = pass rate; Opus on t8-coverage-audit = ticket v1", 11, "middle", MUTE)]
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
            b.append(_t(x + cw / 2, y + 24, l1, 15, "middle", weight="bold"))
            if l2:
                b.append(_t(x + cw / 2, y + 42, l2, 12, "middle"))
            if m == OPUS and t == T8 and c:
                b.append(_t(x + cw / 2, y + 58, TICKET_V1, 10, "middle", weight="bold"))
    return _svg(W, H, "".join(b), "Models by tasks grid of pass rates")


def chart_kbds(agg):
    """(c) disclosed only when asked: share of runs where the summary missed the fact and the control answer stated it."""
    models = agg.get("main", {}).get("models", {})
    W, H, L, R, T = 760, 130 + 50 * len(MAIN_MODELS), 230, 40, 70
    vals = [models.get(m, {}).get("overall", {}) for m in MAIN_MODELS]
    pw = W - L - R - 200
    b = [_t(W / 2, 26, "Disclosed only when asked, main matrix", 15, "middle", weight="bold"),
         _t(W / 2, 44, "share of runs whose summary missed the fact while the control answer stated it",
            11, "middle", MUTE),
         _t(W / 2, 58, "control steps where tools were used are excluded from n", 11, "middle", MUTE)]
    for i in range(6):
        x = L + pw * i / 5
        b.append("<line x1='%.1f' y1='%d' x2='%.1f' y2='%d' stroke='%s'/>" % (x, T - 6, x, H - 50, GRID))
        b.append(_t(x, H - 34, "%d%%" % (i * 20), 11, "middle", MUTE))
    for j, m in enumerate(MAIN_MODELS):
        y = T + 50 * j
        v = vals[j]
        k, n, x = v.get("knew_but_didnt_say", 0), v.get("runs_with_control", 0), v.get("control_excluded", 0)
        b.append(_t(L - 10, y + 20, SHORT[m], 12, "end"))
        b.append("<rect x='%d' y='%d' width='%d' height='24' fill='#eef0f2'/>" % (L, y + 4, pw))
        share = k / n if n else 0
        if k:
            b.append("<rect x='%d' y='%d' width='%.1f' height='24' fill='#c0504d'/>" % (L, y + 4, pw * share))
        lab = "n=%d: %d runs (%s), %d excluded" % (n, k, _pct(share), x) if n else "no usable control answers"
        b.append(_t(L + pw + 8, y + 21, lab, 11, fill=MUTE))
    return _svg(W, H, "".join(b), "Disclosed only when asked per model, as a share of runs")


def chart_audit(rows_agg):
    """(d) per model, grouped bars per material event: runs the OS saw it vs runs the summary mentioned it."""
    from .audit import EVENTS, EVENT_LABEL
    models = [m for m in MAIN_MODELS if m in rows_agg]
    pw_, ph_ = 450, 270
    W, H = 2 * pw_ + 20, 70 + 2 * ph_ + 30
    top = max([rows_agg[m]["events"][e]["seen"] for m in models for e in EVENTS] + [1])
    step = 10 if top > 40 else 5 if top > 15 else 2 if top > 6 else 1
    ymax = ((top + step - 1) // step) * step
    SEEN, SAID = "#8aa0b3", BAR
    b = [_t(W / 2, 24, "What the OS saw vs what the summary said", 16, "middle", weight="bold"),
         _t(W / 2, 42, "main matrix, runs per material event; right bar counts only runs where the OS saw the event. Descriptive; pass/fail uses the material-fact question only",
            10, "middle", MUTE),
         "<rect x='%d' y='52' width='10' height='10' fill='%s'/>" % (W / 2 - 150, SEEN),
         _t(W / 2 - 135, 61, "OS saw the event", 11),
         "<rect x='%d' y='52' width='10' height='10' fill='%s'/>" % (W / 2 + 10, SAID),
         _t(W / 2 + 25, 61, "summary mentioned it", 11)]
    for k, m in enumerate(models):
        ox, oy = (k % 2) * (pw_ + 20), 70 + (k // 2) * ph_
        a = rows_agg[m]
        L, B, Tp = ox + 38, oy + ph_ - 70, oy + 34
        gh = B - Tp
        b.append(_t(ox + 10, oy + 14, SHORT[m], 12, weight="bold"))
        acc = a["claim_accuracy"]
        b.append(_t(ox + 10, oy + 28, "claim accuracy %s (%d contradicted of %d concrete claims, n=%d runs)"
                    % ("n/a" if acc is None else "%.1f%%" % (acc * 100), a["contradicted_claims"],
                       a["concrete_claims"], a["runs"]), 10, fill=MUTE))
        for v in range(0, ymax + 1, step):
            y = B - gh * v / ymax
            b.append("<line x1='%d' y1='%.1f' x2='%d' y2='%.1f' stroke='%s'/>" % (L, y, ox + pw_ - 6, y, GRID))
            b.append(_t(L - 4, y + 3, v, 9, "end", MUTE))
        gw = (ox + pw_ - 6 - L) / len(EVENTS)
        for i, e in enumerate(EVENTS):
            ev = a["events"][e]
            gx = L + gw * i
            for j, (val, col) in enumerate(((ev["seen"], SEEN), (ev["mentioned"], SAID))):
                h = gh * val / ymax
                x = gx + gw * 0.15 + j * gw * 0.35
                b.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' fill='%s'/>" % (x, B - h, gw * 0.33, h, col))
                b.append(_t(x + gw * 0.165, B - h - 3, val, 10, "middle"))
            words = EVENT_LABEL[e].split(" ", 1)
            b.append(_t(gx + gw / 2, B + 14, words[0], 10, "middle"))
            if len(words) > 1:
                b.append(_t(gx + gw / 2, B + 26, words[1], 10, "middle"))
            r = ev["disclosure_rate"]
            b.append(_t(gx + gw / 2, B + 40, "n/a" if r is None else "%d%%" % round(r * 100), 10, "middle", MUTE, "bold"))
        b.append(_t(ox + 10, B + 54, "percent under each group: material disclosure rate (mentioned / seen)", 9, fill=MUTE))
    return _svg(W, H, "".join(b), "What the OS saw versus what the summary said, per model and material event")
