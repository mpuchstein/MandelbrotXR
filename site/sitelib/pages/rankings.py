"""rankings/ — the judge × candidate matrix (sortable, filterable, heatmap), the Kendall-τ
agreement matrix between judges, a bump chart of ranks across judges, and the aggregated
rank table exactly as Judge/README.md shows it.

Everything is discovered from the model: judges, review types, candidates, prompt versions and
judge materials. A judge that did not rank a candidate shows '–' (sorted last).
"""
from __future__ import annotations

import os

from ..fragments import (cand_url, caveats_html, cat, cat_dash, fmt_mean, fmt_score, heat, heat_legend, judge_url,
                         marker_svg, review_url, score_heat)
from ..layout import Site, esc

ORDER = 200

README = "Judge/README.md"


# ---------------------------------------------------------------- small helpers

def _heatvars(style: str) -> str:
    """'background:#abc;color:#fff' (fragments.heat) -> CSS custom properties, so the colours
    only apply when the table carries the .heat-on class."""
    return style.replace("background:", "--hbg:").replace("color:", "--hfg:")


def _material(j) -> str:
    return "browser" if j.browser else "static"


def _num(x: float) -> str:
    """Fixed-format sort key (deterministic)."""
    return f"{x:.4f}"


def fmt_tau(v: float) -> str:
    """'−0.5', '0', '1' — short, with a real minus sign."""
    t = f"{v:g}"
    return t.replace("-", "−")


def _spread_text(lo: int, hi: int, sd: float) -> str:
    rng = f"{lo}" if lo == hi else f"{lo}–{hi}"
    return f"{rng} · σ {sd:.2f}"


GLYPH_W, GLYPH_H, GLYPH_PAD = 96, 18, 6   # rankings.js mirrors these (gx)


def _gx(r: float, n: int) -> str:
    """x position of rank r in the spread glyph (rank 1 at the left end, rank n at the right end)."""
    return f"{GLYPH_PAD + (r - 1) * (GLYPH_W - 2 * GLYPH_PAD) / max(1, n - 1):.1f}"


def _glyph(ranks: dict[str, int], mean: float | None, n: int) -> str:
    """Dot-range glyph on a fixed 1..n scale: faint end ticks at rank 1 and rank n, a line from the best
    to the worst rank, one dot per judge (judges that gave the same rank are stacked vertically, so
    every dot stays visible) and a taller, darker tick at the mean.
    Purely decorative (aria-hidden); the text next to it carries the numbers."""
    if not ranks:
        return ""
    lo, hi = min(ranks.values()), max(ranks.values())
    mid = GLYPH_H / 2
    seen: dict[int, int] = {}
    dots = []
    for jid, r in ranks.items():
        k = seen.get(r, 0)
        seen[r] = k + 1
        dy = 0.0 if k == 0 else (-1) ** k * 3.5 * ((k + 1) // 2)
        dy = max(-mid + 3, min(mid - 3, dy))
        dots.append(f'<circle class="d" data-col="j-{esc(jid)}" data-r="{r}" cx="{_gx(r, n)}" cy="{mid + dy:.1f}" r="2.6"/>')
    ends = "".join(f'<line class="end" x1="{_gx(r, n)}" x2="{_gx(r, n)}" y1="{mid - 4:.1f}" y2="{mid + 4:.1f}"/>' for r in (1, n))
    tick = (f'<line class="mu" x1="{_gx(mean, n)}" x2="{_gx(mean, n)}" y1="0.5" y2="{GLYPH_H - 0.5:.1f}"/>'
            if mean is not None else "")
    return (f'<svg class="rk-glyph" viewBox="0 0 {GLYPH_W} {GLYPH_H}" width="{GLYPH_W}" height="{GLYPH_H}" aria-hidden="true" '
            f'focusable="false" data-n="{n}">'
            f'<line class="axis" x1="{_gx(1, n)}" x2="{_gx(n, n)}" y1="{mid:.1f}" y2="{mid:.1f}"/>{ends}'
            f'<line class="rng" x1="{_gx(lo, n)}" x2="{_gx(hi, n)}" y1="{mid:.1f}" y2="{mid:.1f}"/>{"".join(dots)}{tick}</svg>')


# ---------------------------------------------------------------- the matrix

def _matrix(site: Site) -> tuple[str, str]:
    m = site.model
    judges, rtypes = m.judges, m.review_types
    cands = m.ordered()
    standing = m.standing()
    nmax = max([len(j.rows) for j in judges] or [1])

    def th(key: str, label: str, *, typ: str = "num", first: str = "asc", meta: str = "", cls: str = "",
           extra: str = "", sort: str | None = None, plain: str = "") -> str:
        aria = f' aria-sort="{sort}"' if sort else ""
        return (f'<th scope="col" class="{cls}" data-col="{esc(key)}"{aria}{extra}>'
                f'<button type="button" class="rk-sort" data-col="{esc(key)}" data-type="{typ}" data-first="{first}" data-label="{esc(plain or label)}">'
                f'<span class="rk-label">{label}</span><span class="rk-ind" aria-hidden="true"></span></button>'
                f'{meta}</th>')

    # one header row (the column groups are named in each header: "judge" / "review"), so the
    # header cells line up one-to-one with the body cells and the row can stick on its own
    head = [th("standing", '<span class="sr-only">Standing</span><span aria-hidden="true">#</span>', plain="Standing", cls="num rk-stick rk-stick-1", sort="ascending"),
            th("name", "Candidate", typ="text", cls="rk-stick rk-stick-2")]
    for k, j in enumerate(judges):
        mat = _material(j)
        meta = (f'<span class="rk-meta"><span class="rk-mat rk-mat-{mat}" title="{esc(j.material or mat)}">{mat}</span> '
                f'<a href="{judge_url(j)}" aria-label="{esc(j.label)} judge page">judge</a></span>')
        head.append(th(f"j-{j.id}", f'{esc(j.label)}<span class="sr-only"> judge rank</span>', plain=f"{j.label} judge rank",
                       meta=meta, cls="num rk-judge" + (" rk-first" if k == 0 else ""), extra=f' data-material="{mat}"'))
    head.append(th("mean", plain="Mean rank", label='<span class="rk-l-all">Mean rank</span><span class="rk-l-sub" hidden>Mean over shown judges</span>',
                   meta='<span class="rk-meta"><span class="derived">derived</span></span>', cls="num rk-derived rk-first"))
    head.append(th("spread", plain="Spread", label='<span class="rk-l-all">Spread</span><span class="rk-l-sub" hidden>Spread over shown judges</span>',
                   meta='<span class="rk-meta">min–max · σ <span class="derived">derived</span></span>', cls="rk-derived"))
    for k, (tid, _folder, tlabel) in enumerate(rtypes):
        head.append(th(f"r-{tid}", f'{esc(tlabel)}<span class="sr-only"> review score</span>', plain=f"{tlabel} review score",
                       first="desc", meta='<span class="rk-meta">review · 1–10</span>',
                       cls="num rk-review" + (" rk-first" if k == 0 else "")))

    body = []
    for pos, c in enumerate(cands):
        ranks = m.ranks(c.slug)
        mean = m.mean_rank(c.slug)
        sp = m.spread(c.slug)
        st = standing.get(c.slug)
        if st:
            place, tied = st
            pl = (f'<span title="tied on mean rank">={place}</span><span class="sr-only"> (tie)</span>' if tied else f"{place}")
            cells = [f'<td class="num rk-stick rk-stick-1" data-col="standing" data-sort="{place}">{pl}</td>']
        else:
            why = "not ranked by every judge, so its mean rank is not comparable" if ranks else "not ranked"
            cells = [f'<td class="num rk-stick rk-stick-1 muted" data-col="standing" data-sort="" title="{why}">–'
                     f'<span class="sr-only"> ({why})</span></td>']
        cells.append(f'<th scope="row" class="rk-stick rk-stick-2" data-col="name" data-sort="{esc(c.label.casefold())}">'
                     f'<a href="{cand_url(c)}">{esc(c.label).replace(" · ", "&nbsp;· ")}</a></th>')
        for j in judges:
            r = ranks.get(j.id)
            if r is None:
                cells.append(f'<td class="num muted" data-col="j-{esc(j.id)}" data-sort="" title="not ranked by this judge">–</td>')
            else:
                cells.append(f'<td class="num rk-heat" data-col="j-{esc(j.id)}" data-sort="{r}" '
                             f'style="{_heatvars(heat(r, len(j.rows)))}">{r}</td>')
        if mean is None:
            cells.append('<td class="num muted" data-col="mean" data-sort="">–</td>')
            cells.append('<td class="muted" data-col="spread" data-sort=""><span class="rk-sp">–</span></td>')
        else:
            cov = "" if m.full(c.slug) else (f'<span class="rk-cov" title="ranked by {len(ranks)} of {len(judges)} judges">'
                                             f'{len(ranks)}/{len(judges)} judges</span>')
            cells.append(f'<td class="num rk-mean" data-col="mean" data-sort="{_num(float(mean))}">'
                         f'<span class="rk-mv">{fmt_mean(mean)}</span>{cov}</td>')
            lo, hi, sd = sp
            cells.append(f'<td class="rk-spread" data-col="spread" data-sort="{_num(sd)}">'
                         f'<span class="rk-sp">{esc(_spread_text(lo, hi, sd))}</span>{_glyph(ranks, float(mean), nmax)}</td>')
        for tid, _folder, tlabel in rtypes:
            rv = m.review(tid, c.slug)
            if rv is None:
                cells.append(f'<td class="num muted" data-col="r-{esc(tid)}" data-sort="" title="no {esc(tlabel)} review">–</td>')
            else:
                cells.append(f'<td class="num rk-heat" data-col="r-{esc(tid)}" data-sort="{_num(rv.overall)}" '
                             f'style="{_heatvars(score_heat(rv.overall))}"><a href="{review_url(rv)}" '
                             f'aria-label="{esc(tlabel)} review of {esc(c.label)}: {fmt_score(rv.overall)} out of 10">'
                             f'{fmt_score(rv.overall)}</a></td>')
        body.append(f'<tr data-slug="{esc(c.slug)}" data-prompt="{esc(c.prompt)}" data-order="{pos}">{"".join(cells)}</tr>')

    caption = "Judge ranks (1 = best), derived mean rank and spread, and phase-1 overall scores per candidate."
    # .rk-break lets only the matrix grow past the text column on wide screens; .rk-scroller carries the
    # right-edge fade (rankings.js sets .more-right while columns are hidden to the right)
    table = (f'<p class="rk-scroll-hint small muted" id="rank-scroll-hint">More columns: scroll sideways '
             f'<span aria-hidden="true">→</span></p>'
             f'<div class="rk-break"><div class="rk-scroller" id="rank-scroller">'
             f'<div class="table-wrap matrix-wrap rk-wrap" tabindex="0" role="region" aria-labelledby="matrix-h">'
             f'<table id="rank-matrix" class="rk-matrix" data-nmax="{nmax}">'
             f'<caption class="sr-only">{esc(caption)}</caption>'
             f'<thead><tr>{"".join(head)}</tr></thead><tbody>{"".join(body)}</tbody></table></div></div></div>')

    # controls (hidden without JS; rankings.js unhides them)
    prompts = sorted({c.prompt for c in m.candidates}, key=lambda p: (len(p), p))
    mats = [x for x in ("static", "browser") if any(_material(j) == x for j in judges)]

    def seg(name: str, legend: str, options: list[tuple[str, str]]) -> str:
        opts = "".join(f'<label><input type="radio" name="{name}" value="{esc(v)}"{" checked" if i == 0 else ""}>'
                       f'<span>{esc(lab)}</span></label>' for i, (v, lab) in enumerate(options))
        return f'<fieldset class="rk-seg" data-filter="{name}"><legend>{esc(legend)}</legend><div class="rk-seg-opts">{opts}</div></fieldset>'

    ctrl = []
    if len(prompts) > 1:
        ctrl.append(seg("prompt", "Prompt", [("all", "All")] + [(p, p) for p in prompts]))
    if len(mats) > 1:
        ctrl.append(seg("judges", "Judge material", [("all", "All")] + [(x, x.capitalize()) for x in mats]))
    ctrl.append('<div class="rk-btns"><button type="button" class="btn" id="rank-heat" aria-pressed="false">Heatmap</button>'
                '<button type="button" class="btn" id="rank-reset">Reset view</button></div>')

    # heatmap legend (swatches carry their number: colour is never the only channel)
    sc_sw = "".join(f'<span class="heat-swatch" style="{score_heat(s)}">{s}</span>' for s in range(1, 11))
    legend = (f'<div class="rk-legend" id="heat-legend" hidden>{heat_legend(nmax)}'
              f'<span class="legend-scale" role="note"><span>Score colour: 1</span><span class="heat-swatches" aria-hidden="true">'
              f'{sc_sw}</span><span>10 = best</span></span>'
              f'<span class="small muted">One blue scale, darker = better; the numbers stay in every cell.</span></div>')

    controls = (f'<div class="rk-controls" id="rank-controls" hidden>{"".join(ctrl)}</div>{legend}'
                f'<p class="rk-status small muted" id="rank-status" aria-live="polite" hidden></p>')
    return controls, table


# ---------------------------------------------------------------- Kendall τ

# Dark-theme ramp for τ: low agreement sits close to the dark surface, high agreement is the lightest,
# so salience follows the data in both themes (the light theme uses fragments.score_heat).
_DARK_RAMP = [(31, 38, 51), (37, 55, 86), (48, 79, 128), (70, 112, 176), (110, 152, 214), (162, 194, 238), (212, 227, 250)]


def _rel_lum(rgb: tuple[int, int, int]) -> float:
    def lin(c: int) -> float:
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _tau_style(t: float) -> str:
    """Per-cell custom properties for both themes: --hbg/--hfg (light, the site's single-hue scale)
    and --dbg/--dfg (dark, the inverted-lightness ramp above). Text colour is picked per cell for contrast."""
    x = min(1.0, max(0.0, (t + 1) / 2)) * (len(_DARK_RAMP) - 1)
    i = min(int(x), len(_DARK_RAMP) - 2)
    f = x - i
    rgb = tuple(round(a + (b - a) * f) for a, b in zip(_DARK_RAMP[i], _DARK_RAMP[i + 1]))
    lum = _rel_lum(rgb)
    fg = "#000000" if (lum + 0.05) / 0.05 >= 1.05 / (lum + 0.05) else "#ffffff"  # pure black: >= 4.58:1 at the crossover
    return f"{_heatvars(score_heat(t, -1, 1))};--dbg:#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x};--dfg:{fg}"


def _kendall(site: Site) -> str:
    m = site.model
    js = m.judges
    pairs = {}
    for a, b, t, n in m.kendall_pairs():
        pairs[(a.id, b.id)] = pairs[(b.id, a.id)] = (t, n)

    def cell(t: float | None, n: int, diag: bool = False) -> str:
        if t is None:
            return f'<td class="num rk-tau muted">–<span class="rk-n">n={n}</span></td>'
        txt = "1" if diag else f"{t:.2f}".replace("-", "−")
        return (f'<td class="num rk-tau{" rk-diag" if diag else ""}" style="{_tau_style(t)}">'
                f'{txt}<span class="rk-n">n={n}</span></td>')

    head = "".join(f'<th scope="col" class="num"><a href="{judge_url(j)}">{esc(j.label)}</a></th>' for j in js)
    rows = []
    for a in js:
        cells = []
        others = []
        for b in js:
            if a.id == b.id:
                cells.append(cell(1.0, len(a.rows), diag=True))
            else:
                t, n = pairs[(a.id, b.id)]
                cells.append(cell(t, n))
                if t is not None:
                    others.append(t)
        avg = f"{sum(others) / len(others):.2f}" if others else "–"
        rows.append(f'<tr><th scope="row"><a href="{judge_url(a)}">{esc(a.label)}</a> '
                    f'<span class="rk-mat rk-mat-{_material(a)}">{_material(a)}</span></th>{"".join(cells)}'
                    f'<td class="num rk-avg">{avg}</td></tr>')
    valid = [(a, b, t) for a, b, t, _n in m.kendall_pairs() if t is not None]
    extremes = ""
    if len(valid) > 1:
        hi = lo = valid[0]
        for v in valid[1:]:
            if v[2] > hi[2]:
                hi = v
            if v[2] < lo[2]:
                lo = v
        extremes = (f" Here the closest pair is {esc(hi[0].label)} and {esc(hi[1].label)} (τ = {hi[2]:.2f}); "
                    f"the least similar is {esc(lo[0].label)} and {esc(lo[1].label)} (τ = {lo[2]:.2f}).")
    steps = (-1, -0.5, 0, 0.5, 1)
    sw = "".join(f'<span class="heat-swatch rk-tau-sw" style="{_tau_style(v)}">{fmt_tau(v)}</span>' for v in steps)
    tau_legend = (f'<span class="legend-scale" role="note"><span>τ colour</span><span class="heat-swatches" aria-hidden="true">'
                  f'{sw}</span><span>stronger colour = more agreement</span></span>')
    return f"""
<section aria-labelledby="kendall-h">
<h2 id="kendall-h">How much do the judges agree? <span class="derived">derived</span></h2>
<p>Kendall’s τ<sub>b</sub> between every pair of judges, computed over the candidates both judges ranked (<em>n</em> per pair):</p>
<p class="rk-formula"><span>τ<sub>b</sub> = (C − D) /</span> <span>√((C + D + T<sub>x</sub>)(C + D + T<sub>y</sub>))</span></p>
<p class="small muted">C and D are the numbers of candidate pairs the two judges order the same way (concordant) or the opposite way (discordant); T<sub>x</sub> and T<sub>y</sub> count pairs tied in only one of the two rankings (rankings here have no ties, so τ<sub>b</sub> equals plain Kendall τ). The last column averages a judge’s τ with all the others.</p>
<p><strong>Reading guide:</strong> 1 = identical order, 0 = unrelated, −1 = exactly reversed; the stronger the cell colour, the stronger the agreement.{extremes}</p>
<p class="rk-legend">{tau_legend}</p>
<div class="table-wrap matrix-wrap" tabindex="0" role="region" aria-labelledby="kendall-h">
<table class="rk-kendall">
<caption>Symmetric matrix; the diagonal is 1 by definition (hatched). One blue scale from τ = −1 (faintest) to τ = 1 (strongest: darkest in the light theme, lightest in the dark theme); every cell shows its value.</caption>
<thead><tr><th scope="col">Judge</th>{head}<th scope="col" class="num">Mean τ with others</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
</div>
</section>"""


# ---------------------------------------------------------------- bump chart

def _bump(site: Site) -> str:
    m = site.model
    js = m.judges
    if not js:
        return ""
    cands = [c for c in m.ordered() if m.ranks(c.slug)]
    n = max(len(j.rows) for j in js)
    row_h, top, bottom = 36, 64, 20
    left, right, axis = 170, 170, 28
    step = 120
    plot_w = max(step, (len(js) - 1) * step)
    width = axis + left + plot_w + right
    height = top + (n - 1) * row_h + bottom
    x0 = axis + left
    xs = [x0 + (plot_w / 2 if len(js) == 1 else i * plot_w / (len(js) - 1)) for i in range(len(js))]
    y = lambda r: top + (r - 1) * row_h

    parts = []
    # recessive grid + judge headers
    for r in range(1, n + 1):
        parts.append(f'<line class="grid-line" x1="{x0 - 8:.1f}" x2="{x0 + plot_w + 8:.1f}" y1="{y(r):.1f}" y2="{y(r):.1f}"/>')
        parts.append(f'<text class="label-muted rk-axis" x="10" y="{y(r) + 4:.1f}">{r}</text>')
    parts.append(f'<text class="label-muted rk-axis" x="10" y="{top - 26:.1f}">rank</text>')
    for j, x in zip(js, xs):
        parts.append(f'<line class="axis" x1="{x:.1f}" x2="{x:.1f}" y1="{top - 12:.1f}" y2="{y(n) + 10:.1f}"/>')
        bits = j.label.split(" + ")
        lines = [bits[0]] + [f"+ {b}" for b in bits[1:]]
        y0 = top - 44 + (2 - min(len(lines), 2)) * 14
        tspans = "".join(f'<tspan x="{x:.1f}" dy="{0 if k == 0 else 14}">{esc(t)}</tspan>' for k, t in enumerate(lines))
        parts.append(f'<text class="rk-jh" x="{x:.1f}" y="{y0:.1f}" text-anchor="middle">{tspans}</text>')
        parts.append(f'<text class="label-muted rk-jm" x="{x:.1f}" y="{top - 16:.1f}" text-anchor="middle">{_material(j)}</text>')

    desc = []
    for c in reversed(cands):  # draw the best last so it sits on top
        ranks = m.ranks(c.slug)
        pts = [(x, ranks.get(j.id)) for j, x in zip(js, xs)]
        segs, cur = [], []
        for x, r in pts:
            if r is None:
                if cur:
                    segs.append(cur)
                cur = []
            else:
                cur.append((x, r))
        if cur:
            segs.append(cur)
        lines = ""
        dash = f' stroke-dasharray="{cat_dash(c.index)}"' if cat_dash(c.index) else ""
        for s in segs:
            p = " ".join(f"{x:.1f},{y(r):.1f}" for x, r in s)
            if len(s) > 1:
                lines += (f'<polyline class="hit" points="{p}"/><polyline class="case" points="{p}"/>'
                          f'<polyline class="ln" points="{p}"{dash}/>')
        marks = "".join(marker_svg(c.index, x, y(r), r=5.5) for x, r in pts if r is not None)
        known = [(x, r) for x, r in pts if r is not None]
        (lx, lr), (rx, rr) = known[0], known[-1]
        labels = (f'<text class="rk-bl" x="{x0 - 16:.1f}" y="{y(lr) + 4:.1f}" text-anchor="end">{esc(c.label)}</text>'
                  f'<text class="rk-bl" x="{x0 + plot_w + 16:.1f}" y="{y(rr) + 4:.1f}">{esc(c.label)}</text>')
        parts.append(f'<g class="rk-series" style="--c:{cat(c.index)}">{lines}<g class="mk">{marks}</g>{labels}</g>')
    for c in cands:
        ranks = m.ranks(c.slug)
        desc.append(f"{c.label}: " + ", ".join(f"{j.label} {ranks.get(j.id, '–')}" for j in js))
    desc_txt = ("Rank of each candidate (1 = best, at the top) for each judge, left to right in the order "
                + ", ".join(j.label for j in js) + ". " + "; ".join(desc) + ".")
    svg = (f'<svg class="chart rk-bump" viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
           f'aria-labelledby="bump-title bump-desc" preserveAspectRatio="xMinYMin meet">'
           f'<title id="bump-title">Bump chart: each candidate’s rank across the judges</title>'
           f'<desc id="bump-desc">{esc(desc_txt)}</desc>{"".join(parts)}</svg>')
    return f"""
<section aria-labelledby="bump-h">
<h2 id="bump-h">Ranks across judges</h2>
<p>One line per candidate, from judge to judge (rank 1 at the top). Flat lines mean the judges agree; crossings are dissents. Each line is labelled at both ends, so colour is not needed to follow it; every candidate keeps the same colour (and, past eight candidates, the same dash pattern and marker shape) in every chart on this site. The <a href="#matrix-h">judge × candidate matrix</a> above is this chart’s table equivalent.</p>
<div class="rk-chart-scroll" tabindex="0" role="region" aria-label="Bump chart (scrolls sideways on narrow screens)">{svg}</div>
</section>"""


# ---------------------------------------------------------------- page

def build(site: Site) -> None:
    m = site.model
    controls, table = _matrix(site)
    judges, rtypes = m.judges, m.review_types
    ranked = [c for c in m.candidates if m.ranks(c.slug)]

    # aggregated table: identical to Judge/README.md?
    agg = m.rank_table_md()
    readme_path = os.path.join(site.repo, README)
    readme = open(readme_path, encoding="utf-8").read() if os.path.isfile(readme_path) else ""
    if agg in readme:
        same = f'It reproduces the table in {site.evidence(README, "Judge/README.md")} character for character (checked at build time).'
    else:
        same = (f'<strong>It differs from the table in {site.evidence(README, "Judge/README.md")}</strong> '
                f'(checked at build time), for example because a judgment was added after that README was written.')
    evid = "".join(f'<li>{esc(j.label)} judge: {site.evidence(j.files["RANKING.md"], j.folder + "/RANKING.md")}'
                   + (f' · {site.evidence(j.files["MAPPING.md"], "MAPPING.md")}' if "MAPPING.md" in j.files else "")
                   + "</li>" for j in judges if "RANKING.md" in j.files)

    n_j, n_c, n_t = len(judges), len(ranked), len(rtypes)
    mats = sorted({_material(j) for j in judges})
    body = f"""
<h1>Rankings</h1>
<p class="lede">{n_j} blind judges each ranked the candidates from best to worst; {n_t} kinds of blind phase-1 review scored each one from 1 to 10. This page puts every number side by side. Sort any column, filter by prompt or by what the judges could see, and switch on the heatmap.</p>

<section aria-labelledby="matrix-h">
<h2 id="matrix-h">Judge × candidate matrix</h2>
{controls}
{table}
<p class="small muted">Default order: by mean rank, ties as in Judge/README.md. Mean rank and Spread are derived from the judge columns; each phase-1 score links to its review. On narrow screens the table scrolls sideways inside its frame. Phase-1 scores come from {site.evidence("ReviewOrchestrator/README.md", "ReviewOrchestrator/README.md §4")}; judge ranks from each judge’s <code>RANKING.md</code> (listed at the bottom of this page) via {site.evidence("Judge/judge-mapping.json", "Judge/judge-mapping.json")}.</p>
</section>

<section aria-labelledby="read-h" class="rk-read">
<h2 id="read-h">How to read this</h2>
<div class="note">
<ul>
<li><strong>Rank 1 = best.</strong> Each judge column is one judge’s blind ranking of all candidates it saw. A dash (–) means that judge did not rank that candidate.</li>
<li><strong>Mean rank</strong> <span class="derived">derived</span> is the arithmetic mean of a candidate’s ranks over the judges that ranked it (over the judges currently shown, when you filter by material). Equal means are ties and are shown as ties: “=1” means shared first place. The standing (#) is only given to candidates ranked by every judge; a candidate that some judges did not rank shows how many did (e.g. “4/5 judges”) and is listed after the others.</li>
<li><strong>Spread</strong> <span class="derived">derived</span> gives the best and worst rank a candidate received (min–max) and σ, the population standard deviation of its ranks across judges: σ = √(Σ(r − mean)² / n). A large σ marks a controversial candidate. In the glyph, the faint end ticks mark rank 1 (left) and the last rank (right), each dot is one judge (equal ranks stack vertically) and the tall tick is the mean.</li>
<li><strong>Phase-1 scores</strong> are the 1–10 overall scores from separate blind reviews (one reviewer per review type and candidate), not from the judges. Click a score to read the review.</li>
<li><strong>Judge material:</strong> {", ".join(f"“{x}”" for x in mats)} — static judges read code and/or transcripts only; browser judges used the product hands-on in desktop Chrome.</li>
<li><strong>v0 and v1</strong> are different prompts; each candidate was judged against its own prompt, in one combined ranking.</li>
</ul>
</div>
{caveats_html(compact=True)}
</section>
{_kendall(site)}
{_bump(site)}

<section aria-labelledby="agg-h">
<h2 id="agg-h">Sources</h2>
<details class="fold">
<summary>Aggregated rank table (Markdown, as in Judge/README.md)</summary>
<p class="small">Generated by this build from the judges’ rankings and the letter mapping, in the format of <code>judge_aggregate.py</code>. {same}</p>
<pre class="rk-agg"><code>{esc(agg)}</code></pre>
</details>
<h3>Judge rankings</h3>
<ul class="rk-evidence small">{evid}</ul>
</section>
"""
    site.page("rankings/index.html", "Rankings", body, section="rankings", crumbs=[("Rankings", "rankings/")],
              description="Sortable judge × candidate rank matrix with mean rank, spread, phase-1 scores, "
                          "judge agreement (Kendall τ) and a bump chart.",
              scripts=["rankings.js"])

    # search document
    st = m.standing()
    lines = []
    for c in m.ordered():
        r = m.ranks(c.slug)
        if not r:
            continue
        place, tied = st.get(c.slug, ("–", False))
        sc = ", ".join(f"{tl} review {fmt_score(m.review(t, c.slug).overall)}" for t, _f, tl in rtypes if m.review(t, c.slug))
        lines.append(f"{'=' if tied else ''}{place} {c.name} ({c.prompt}): mean rank {fmt_mean(m.mean_rank(c.slug))}; "
                     + ", ".join(f"{j.label} judge {r[j.id]}" for j in judges if j.id in r) + (f"; {sc}" if sc else "") + ".")
    site.search_doc("rankings/", "Rankings", "page", "Judge × candidate matrix",
                    "Rankings: mean rank, spread (σ), Kendall tau agreement between judges, bump chart. " + " ".join(lines))
