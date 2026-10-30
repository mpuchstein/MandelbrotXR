"""Shared URLs, colours and text fragments for page modules (keep page logic out of here)."""
from __future__ import annotations

from .data import Candidate, Judge, Model, Review, fmt_mean, fmt_score
from .layout import Site, esc

__all__ = ["cand_url", "play_url", "judge_url", "review_url", "compare_url", "cat", "cat_dash", "cat_marker",
           "marker_svg", "heat", "score_heat", "heat_legend",
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


# single-hue sequential ramp (Mandelbrot deep blue), light -> dark; colour is never the only channel
_RAMP = [(239, 243, 250), (198, 214, 238), (148, 178, 222), (95, 138, 199), (52, 99, 168), (25, 64, 128), (12, 36, 82)]


def _lerp(t: float) -> tuple[int, int, int]:
    t = min(1.0, max(0.0, t)) * (len(_RAMP) - 1)
    i = min(int(t), len(_RAMP) - 2)
    f = t - i
    return tuple(round(a + (b - a) * f) for a, b in zip(_RAMP[i], _RAMP[i + 1]))


def _style(rgb: tuple[int, int, int]) -> str:
    def lin(c: int) -> float:
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    lum = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    fg = "#111111" if (lum + 0.05) / 0.05 >= 1.05 / (lum + 0.05) else "#ffffff"
    return f"background:#{r:02x}{g:02x}{b:02x};color:{fg}"


def heat(rank: float, n: int) -> str:
    """Inline style for a rank cell (single-hue scale): rank 1 = darkest blue, rank n = lightest.
    The rank number stays printed in the cell; pair with heat_legend()."""
    return _style(_lerp(1 - (rank - 1) / max(1, n - 1)))


def score_heat(score: float, lo: float = 0, hi: float = 10) -> str:
    """Inline style for a 1–10 score cell (same single-hue scale): higher = darker."""
    return _style(_lerp((score - lo) / (hi - lo)))


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
