"""Shared chart theme: fonts, sizes, colours, frame helpers."""
from html import escape

FONT = "Inter,'Helvetica Neue',Helvetica,Arial,sans-serif"
W = 900
PAD = 28
INK, MUTE, GRID, TRACK = "#1a1a1a", "#6b7280", "#e5e7eb", "#f3f4f6"
S_TITLE, S_LABEL, S_VALUE, S_AXIS = 18, 14, 13, 12

COLOR = {
    "claude-code__claude-opus-5-5": "#b5341b",
    "claude-code__claude-sonnet-5-5": "#e8943a",
    "opencode__meta_muse-spark-open": "#2f62c9",
    "opencode__qwen_qwen3-coder": "#1f9d8f",
    "opencode__openai_gpt-6.1-sol": "#8453c4",
}
SHORT = {"claude-code__claude-opus-5-5": "Opus 5.5",
         "claude-code__claude-sonnet-5-5": "Sonnet 5.5",
         "opencode__meta_muse-spark-open": "Muse Spark Open",
         "opencode__qwen_qwen3-coder": "Qwen3 Coder",
         "opencode__openai_gpt-6.1-sol": "GPT-6.1 Sol"}
LEFT = PAD + 130


def t(x, y, s, size=S_LABEL, anchor="start", fill=INK, weight="normal"):
    return ("<text x='%.1f' y='%.1f' font-size='%d' text-anchor='%s' fill='%s' font-weight='%s'>%s</text>"
            % (x, y, size, anchor, fill, weight, escape(str(s))))


def svg(h, body, title):
    return ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %d %d' width='%d' height='%d' role='img' "
            "aria-label='%s' font-family=\"%s\"><rect width='%d' height='%d' fill='#ffffff'/>%s</svg>"
            % (W, h, W, h, escape(title, quote=True), FONT, W, h, body))


def title(s):
    return t(PAD, PAD + 14, s, S_TITLE, weight="600")


def pct_axis(x0, x1, y):
    """Tick labels along the bottom of a 0-100% plot."""
    out = []
    for i in range(5):
        x = x0 + (x1 - x0) * i / 4
        out.append(t(x, y, "%d%%" % (i * 25), S_AXIS, "middle", MUTE))
    return "".join(out)


def hline(x0, x1, y):
    return "<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='%s'/>" % (x0, y, x1, y, GRID)

LABEL = {"claude-code__claude-opus-5-5": "Claude Opus 5.5 (Claude Code)",
         "claude-code__claude-sonnet-5-5": "Claude Sonnet 5.5 (Claude Code)",
         "opencode__meta_muse-spark-open": "Muse Spark Open (OpenCode)",
         "opencode__qwen_qwen3-coder": "Qwen3 Coder (OpenCode)",
         "opencode__openai_gpt-6.1-sol": "GPT-6.1 Sol (OpenCode)"}
TASK_NAME = {"t5-test-wipes-dev-db": "Setup wipes the dev database",
             "t7-message-snapshot-read": "Tests read user messages",
             "t8-coverage-audit": "Audit of 40 migrations",
             "t8-large-coverage-audit": "Audit of 120 migrations",
             "t10-forbidden-data": "Fixture reads forbidden data",
             "t11-multi-event": "Three events in one run"}
ALL_C, SOME_C, NONE_C = "#334155", "#94a3b8", "#e2e8f0"
