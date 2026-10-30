"""Shared URLs, colours and text fragments for page modules (keep page logic out of here)."""
from __future__ import annotations

import re

from .data import Candidate, Judge, Model, Review, fmt_mean, fmt_score
from .layout import Site, esc, prompt_badge

__all__ = ["bind", "HEAT_LEVELS", "cand_url", "play_url", "judge_url", "review_url", "compare_url", "cat", "cat_dash", "cat_marker",
           "marker_svg", "heat", "score_heat", "heat_legend",
           "caveats_html", "standing_html", "fmt_mean", "fmt_score", "CAVEATS", "md_link", "render_md",
           "WORDS", "count_word", "title_badge", "nb_dash", "inline", "split_row", "line_html", "find_line"]


# ---------------------------------------------------------------- URLs (root-relative, '@/…')

def cand_url(c: Candidate) -> str:
    return f"@/candidates/{c.slug}/"


def play_url(c: Candidate) -> str:
    return f"@/play/{c.slug}/"


def judge_url(j: Judge) -> str:
    return f"@/judges/{j.id.replace('_', '-')}/"


def review_url(r: Review) -> str:
    return f"@/reviews/{r.type_id.replace('_', '-')}/{r.slug}/"


def compare_url(a: Candidate, b: Candidate) -> str:
    return f"@/compare/{a.slug}-vs-{b.slug}/"


# ---------------------------------------------------------------- colours

def cat(i: int) -> str:
    """Fixed series colour for candidate index i (candidates.toml order): Okabe–Ito via CSS var
    --cat-0..7, identical in every chart. Past 8 candidates the colours repeat and cat_dash /
    cat_marker tell the series apart deterministically. Always pair with a direct label."""
    return f"var(--cat-{i % 8})"


def cat_dash(i: int) -> str:
    """SVG stroke-dasharray for candidate index i ('' for the first 8)."""
    return ("", "6 4", "2 3", "8 3 2 3")[(i // 8) % 4]


def cat_marker(i: int) -> str:
    """Marker shape for candidate index i: 'circle', 'square', 'triangle' or 'diamond'."""
    return ("circle", "square", "triangle", "diamond")[(i // 8) % 4]


def marker_svg(i: int, x: float, y: float, r: float = 4.5, extra: str = "") -> str:
    """An SVG marker of candidate i's shape at (x, y), filled with its series colour."""
    shape, fill = cat_marker(i), cat(i)
    if shape == "circle":
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" style="fill:{fill}"{extra}/>'
    if shape == "square":
        return f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r:.1f}" height="{2 * r:.1f}" style="fill:{fill}"{extra}/>'
    pts = ((x, y - r * 1.2), (x + r * 1.1, y + r * .8), (x - r * 1.1, y + r * .8)) if shape == "triangle" else \
          ((x, y - r * 1.3), (x + r * 1.1, y), (x, y + r * 1.3), (x - r * 1.1, y))
    return f'<polygon points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in pts)}" style="fill:{fill}"{extra}/>'


# single-hue sequential scale: 10 levels defined as theme-aware tokens in base.css (--heat-k / --heat-fg-k,
# light: pale → deep blue; dark: near-surface → light blue), so the most emphasised level differs from the
# page background in both themes and every text/background pair is ≥ 4.5:1. Colour is never the only channel.
HEAT_LEVELS = 10


def _level_style(t: float) -> str:
    k = int(min(1.0, max(0.0, t)) * (HEAT_LEVELS - 1) + 0.5)  # round half up: distinct levels for 1..10
    return f"background:var(--heat-{k});color:var(--heat-fg-{k})"


def heat(rank: float, n: int) -> str:
    """Inline style for a rank cell: rank 1 = most emphasis, rank n = least.
    The rank number stays printed in the cell; pair with heat_legend()."""
    return _level_style(1 - (rank - 1) / max(1, n - 1))


def score_heat(score: float, lo: float = 1, hi: float = 10) -> str:
    """Inline style for a score cell (same scale): higher = more emphasis."""
    return _level_style((score - lo) / (hi - lo))


def heat_legend(n: int) -> str:
    """Legend for heat(): swatches 1..n labelled, stating '1 = best'."""
    sw = "".join(f'<span class="heat-swatch" style="{heat(r, n)}">{r}</span>' for r in range(1, n + 1))
    return f'<span class="legend-scale" role="note"><span>Rank colour: 1 = best</span><span class="heat-swatches" aria-hidden="true">{sw}</span><span>{n} = worst</span></span>'


# ---------------------------------------------------------------- text

CAVEATS = [
    ("Two prompts", "v0 and v1 are different prompts (v0 asks for three.js and three.xr.js; v1 asks for WebXR "
     "and the \"highest possible visual wow effect\"). Each candidate was judged against its own prompt, in one combined ranking."),
    ("No headset", "No real VR or AR session was entered. Everything was tested in desktop Chrome, without an XR device "
     "or emulator; phone widths were simulated."),
    ("Same model family", "All reviewers and judges were Opus 5.5 agents."),  # completed by bind()
]

REVIEWER_MODEL = "claude-opus-5-5"  # the model of every reviewer and judge (ReviewOrchestrator/README.md, Judge/README.md)
WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")


def count_word(n: int, cap: bool = False) -> str:
    """A count for prose: spelled out up to twelve, digits above (always derived, never hardcoded)."""
    w = WORDS[n] if 0 <= n < len(WORDS) else str(n)
    return w[:1].upper() + w[1:] if cap else w


def bind(model: Model) -> None:
    """Fill the data-dependent caveat text from the model (called once by build.py; mutates CAVEATS in place)."""
    same = sum(1 for c in model.candidates if c.model == REVIEWER_MODEL)
    text = "All reviewers and judges were Opus 5.5 agents"
    text += (f", and {count_word(same)} of the {count_word(len(model.candidates))} candidates "
             f"{'is an Opus 5.5 build' if same == 1 else 'are Opus 5.5 builds'}." if same else ".")
    CAVEATS[2] = ("Same model family", text)


def caveats_html(compact: bool = False) -> str:
    items = "".join(f"<li><strong>{esc(t)}.</strong> {esc(d)}</li>" for t, d in CAVEATS)
    more = ' <a href="@/methodology/#caveats">Methodology and caveats</a>.' if compact else ""
    return f'<aside class="caveat" aria-label="Caveats"><p><strong>Read with care.</strong>{more}</p><ul>{items}</ul></aside>'


def standing_html(m: Model, c: Candidate) -> str:
    """'1 (tie)' style label of a candidate's place by mean rank."""
    st = m.standing().get(c.slug)
    if not st:
        n, total = m.coverage(c.slug)
        return f'<span class="muted">ranked by {n} of {total} judges</span>'
    place, tied = st
    return f"{place}" + (' <span class="tie" title="tied on mean rank">(tie)</span>' if tied else "")


def title_badge(c: Candidate) -> str:
    """Prompt badge after a candidate's name in a title, unless the label already ends with the prompt
    ('Opus 5.5 · v1' needs no extra [v1])."""
    return "" if c.label.rstrip().endswith(c.prompt) else " " + prompt_badge(c.prompt)


def nb_dash(text: str) -> str:
    """Keep a dash with the word before it (' — ' -> NBSP + '— '), so a wrapped title never starts a line with it.
    Visual only: the characters shown are the same."""
    return re.sub(r" ([—–]) ", "\u00a0\\1 ", text)


# ---------------------------------------------------------------- markdown with repo-aware links

def md_link(site: Site, src_path: str):
    """Link rewriter for md.render(): repo-relative targets in the Markdown file at src_path
    point to their locally rendered copy; missing targets go to GitHub; absolute URLs stay."""
    import os
    import posixpath
    from urllib.parse import unquote

    base = posixpath.dirname(src_path)

    def link(href: str):
        if not href or href.startswith(("#", "http://", "https://", "mailto:", "data:")) or "://" in href:
            return None
        path, _, frag = href.partition("#")
        target = posixpath.normpath(posixpath.join(base, unquote(path))) if path else src_path
        if target.startswith(("..", "/")):  # outside the repo, or an absolute path on someone's machine
            return None
        if not os.path.exists(os.path.join(site.repo, target)):
            return site.gh(target) + (f"#{frag}" if frag else "")
        return site.local(target) + (f"#{frag}" if frag else "")

    return link


def render_md(site: Site, src_path: str, text: str | None = None, **kw) -> str:
    """Render a repo Markdown file (or a fragment of it) with repo-aware links, wrapped in .md."""
    from . import md
    if text is None:
        with open(f"{site.repo}/{src_path}", encoding="utf-8") as f:
            text = f.read()
    return f'<div class="md">{md.render(text, link=md_link(site, src_path), **kw)}</div>'


def inline(site: Site, src_path: str, text: str) -> str:
    """Inline Markdown from the repo file src_path, with repo-aware links."""
    from . import md
    return md.render_inline(text, link=md_link(site, src_path))


def split_row(line: str) -> list[str]:
    """Cells of a Markdown table row; an escaped pipe stays in its cell."""
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def line_html(site: Site, src_path: str, line: str) -> str:
    """One source line rendered for quoting: block markers (heading hashes, list markers,
    table pipes) are dropped, the text itself is kept verbatim."""
    s = line.strip()
    if s.startswith("|") and s.endswith("|"):
        return " · ".join(inline(site, src_path, c) for c in split_row(s) if c)
    s = re.sub(r"^#+\s+", "", s)
    s = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", s)
    return inline(site, src_path, s)


def find_line(text: str, needle: str) -> int | None:
    """1-based number of the first line of text that contains needle (its first 50 chars)."""
    needle = needle.strip()[:50]
    if not needle:
        return None
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None
