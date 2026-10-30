"""Shared URLs, colours and text fragments for page modules (keep page logic out of here)."""
from __future__ import annotations

from .data import Candidate, Judge, Model, Review, fmt_mean, fmt_score
from .layout import Site, esc

__all__ = ["cand_url", "play_url", "judge_url", "review_url", "compare_url", "cat", "heat", "score_heat",
           "caveats_html", "standing_html", "fmt_mean", "fmt_score", "CAVEATS", "md_link", "render_md"]


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
    """Categorical colour for candidate index i (Okabe–Ito based, theme-aware CSS variable)."""
    return f"var(--cat-{i % 8})"


# cividis-like sequential ramp (colour-blind safe, perceptually ordered), dark -> light
_RAMP = [(0, 34, 78), (37, 60, 107), (87, 92, 109), (124, 123, 120), (164, 157, 114), (205, 193, 96), (253, 232, 69)]


def _lerp(t: float) -> tuple[int, int, int]:
    t = min(1.0, max(0.0, t)) * (len(_RAMP) - 1)
    i = min(int(t), len(_RAMP) - 2)
    f = t - i
    return tuple(round(a + (b - a) * f) for a, b in zip(_RAMP[i], _RAMP[i + 1]))


def _style(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    lum = 0.2126 * (r / 255) ** 2.2 + 0.7152 * (g / 255) ** 2.2 + 0.0722 * (b / 255) ** 2.2
    fg = "#111" if lum > 0.22 else "#fff"
    return f"background:#{r:02x}{g:02x}{b:02x};color:{fg}"


def heat(rank: float, n: int) -> str:
    """Inline style for a rank cell: rank 1 = brightest, rank n = darkest."""
    return _style(_lerp(1 - (rank - 1) / max(1, n - 1)))


def score_heat(score: float, lo: float = 0, hi: float = 10) -> str:
    """Inline style for a 1–10 score cell: higher = brighter."""
    return _style(_lerp((score - lo) / (hi - lo)))


# ---------------------------------------------------------------- text

CAVEATS = [
    ("Two prompts", "v0 and v1 are different prompts (v0 asks for three.js and three.xr.js; v1 asks for WebXR "
     "and the \"highest possible visual wow effect\"). Each candidate was judged against its own prompt, in one combined ranking."),
    ("No headset", "No real VR or AR session was entered. Everything was tested in desktop Chrome, without an XR device "
     "or emulator; phone widths were simulated."),
    ("Same model family", "All reviewers and judges were Opus 5.5 agents, and two of the eight candidates are Opus 5.5 builds."),
]


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
        if target.startswith(".."):
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
