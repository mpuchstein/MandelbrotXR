"""rankings/ — the judge × candidate matrix (sortable, filterable, heatmap), the Kendall-τ
agreement matrix between judges, a bump chart of ranks across judges, and the aggregated
rank table exactly as Judge/README.md shows it.

Everything is discovered from the model: judges, review types, candidates, prompt versions and
judge materials. A judge that did not rank a candidate shows '–' (sorted last).
"""
from __future__ import annotations

import math
import os

from ..fragments import (cand_url, caveats_html, cat, cat_dash, fmt_mean, fmt_score, heat, heat_legend, judge_url,
                         review_url, score_heat)
from ..layout import Site, esc, prompt_badge

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


def _spread_text(lo: int, hi: int, sd: float) -> str:
    rng = f"{lo}" if lo == hi else f"{lo}–{hi}"
    return f"{rng} · σ {sd:.2f}"


def _gx(r: float, n: int) -> str:
    """x position of rank r in the 64-unit-wide spread glyph."""
    return f"{4 + (r - 1) * 56 / max(1, n - 1):.1f}"


def _glyph(ranks: dict[str, int], mean: float | None, n: int) -> str:
    """Tiny dot-range glyph: a line from min to max rank, one dot per judge, a tick at the mean.
    Purely decorative (aria-hidden); the text next to it carries the numbers."""
    if not ranks:
        return ""
    lo, hi = min(ranks.values()), max(ranks.values())
    dots = "".join(f'<circle class="d" data-col="j-{esc(jid)}" data-r="{r}" cx="{_gx(r, n)}" cy="7" r="2.6"/>'
                   for jid, r in ranks.items())
    tick = (f'<line class="mu" x1="{_gx(mean, n)}" x2="{_gx(mean, n)}" y1="1.5" y2="12.5"/>' if mean is not None else "")
    return (f'<svg class="rk-glyph" viewBox="0 0 64 14" width="64" height="14" aria-hidden="true" focusable="false" data-n="{n}">'
            f'<line class="axis" x1="4" x2="60" y1="7" y2="7"/>'
            f'<line class="rng" x1="{_gx(lo, n)}" x2="{_gx(hi, n)}" y1="7" y2="7"/>{dots}{tick}</svg>')


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

    span2 = ' rowspan="2"'
    head = [th("standing", '<span class="sr-only">Place</span><span aria-hidden="true">#</span>', plain="Place", cls="num rk-stick rk-stick-1", sort="ascending", extra=span2),
            th("name", "Candidate", typ="text", cls="rk-stick rk-stick-2", extra=span2)]
    if judges:
        head.append(f'<th scope="colgroup" colspan="{len(judges)}" class="rk-group" id="rk-g-judges">'
                    f'Judges <span class="rk-gsub">phase 2 · rank, 1 = best</span></th>')
    sub = []
    for j in judges:
        mat = _material(j)
        meta = (f'<span class="rk-meta"><span class="rk-mat rk-mat-{mat}" title="{esc(j.material or mat)}">{mat}</span> '
                f'<a href="{judge_url(j)}" aria-label="{esc(j.label)} judge page">judge</a></span>')
        sub.append(th(f"j-{j.id}", esc(j.label), meta=meta, cls="num rk-judge",
                      extra=f' data-material="{mat}"'))
    head.append(th("mean", plain="Mean rank", label='<span class="rk-l-all">Mean rank</span><span class="rk-l-sub" hidden>Mean over shown judges</span>',
                   meta='<span class="rk-meta"><span class="derived">derived</span></span>', cls="num rk-derived", extra=span2))
    head.append(th("spread", plain="Spread", label='<span class="rk-l-all">Spread</span><span class="rk-l-sub" hidden>Spread over shown judges</span>',
                   meta='<span class="rk-meta">min–max · σ <span class="derived">derived</span></span>', cls="rk-derived",
                   extra=span2))
    if rtypes:
        head.append(f'<th scope="colgroup" colspan="{len(rtypes)}" class="rk-group rk-group-r">'
                    f'Phase-1 reviews <span class="rk-gsub">overall score, 1–10</span></th>')
    for tid, _folder, tlabel in rtypes:
        sub.append(th(f"r-{tid}", esc(tlabel), first="desc",
                      meta='<span class="rk-meta">review</span>', cls="num rk-review"))

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
        cells.append(f'<th scope="row" class="rk-stick rk-stick-2" data-col="name" data-sort="{esc(c.name.casefold())}">'
                     f'<a href="{cand_url(c)}">{esc(c.name).replace(" · ", "&nbsp;· ")}</a> {prompt_badge(c.prompt)}</th>')
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
                             f'aria-label="{esc(tlabel)} review of {esc(c.name)}: {fmt_score(rv.overall)} out of 10">'
                             f'{fmt_score(rv.overall)}</a></td>')
        body.append(f'<tr data-slug="{esc(c.slug)}" data-prompt="{esc(c.prompt)}" data-order="{pos}">{"".join(cells)}</tr>')

    caption = "Judge ranks (1 = best), derived mean rank and spread, and phase-1 overall scores per candidate."
    table = (f'<div class="table-wrap rk-wrap" tabindex="0" role="region" aria-labelledby="matrix-h">'
             f'<table id="rank-matrix" class="rk-matrix" data-nmax="{nmax}">'
             f'<caption class="sr-only">{esc(caption)}</caption>'
             f'<thead><tr>{"".join(head)}</tr><tr>{"".join(sub)}</tr></thead><tbody>{"".join(body)}</tbody></table></div>')

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

def _kendall(site: Site) -> str:
    m = site.model
    js = m.judges
    pairs = {}
    for a, b, t, n in m.kendall_pairs():
        pairs[(a.id, b.id)] = pairs[(b.id, a.id)] = (t, n)

    def cell(t: float | None, n: int, diag: bool = False) -> str:
        if t is None:
            return f'<td class="num rk-tau muted">–<span class="rk-n">n={n}</span></td>'
        mix = round(abs(t) * 40)
        sign = "pos" if t > 0 else "neg" if t < 0 else "zero"
        txt = "1" if diag else f"{t:.2f}"
        return (f'<td class="num rk-tau rk-tau-{sign}{" rk-diag" if diag else ""}" style="--mix:{mix}%">'
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
    neg_note = " (accent colour for agreement, red for negative τ)" if any(v[2] < 0 for v in valid) else ""
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
    return f"""
<section aria-labelledby="kendall-h">
<h2 id="kendall-h">How much do the judges agree? <span class="derived">derived</span></h2>
<p>Kendall’s τ<sub>b</sub> between every pair of judges, computed over the candidates both judges ranked (<em>n</em> per pair):</p>
<p class="rk-formula"><span>τ<sub>b</sub> = (C − D) / √((C + D + T<sub>x</sub>)(C + D + T<sub>y</sub>))</span></p>
<p class="small muted">C and D are the numbers of candidate pairs the two judges order the same way (concordant) or the opposite way (discordant); T<sub>x</sub> and T<sub>y</sub> count pairs tied in only one of the two rankings (rankings here have no ties, so τ<sub>b</sub> equals plain Kendall τ). The last column averages a judge’s τ with all the others.</p>
<p><strong>Reading guide:</strong> 1 = identical order, 0 = unrelated, −1 = exactly reversed; darker cells mean stronger agreement.{extremes}</p>
<div class="table-wrap" tabindex="0" role="region" aria-labelledby="kendall-h">
<table class="rk-kendall">
<caption>Symmetric matrix; the diagonal is 1 by definition (hatched). Shading deepens with |τ|{neg_note}; every cell shows its value.</caption>
<thead><tr><th scope="col">Judge</th>{head}<th scope="col" class="num">Mean τ with others</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
</div>
</section>"""


# ---------------------------------------------------------------- bump chart

def _shape(i: int, x: float, y: float, r: float = 5.5) -> str:
    """Marker shape per candidate index (a second channel next to colour and the direct labels)."""
    k = i % 8
    if k == 0:
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>'
    if k == 1:
        s = r * .9
        return f'<rect x="{x - s:.1f}" y="{y - s:.1f}" width="{2 * s:.1f}" height="{2 * s:.1f}"/>'
    sides, rot, star = {2: (4, 0, False), 3: (3, -90, False), 4: (3, 90, False), 5: (5, -90, False),
                        6: (6, 0, False), 7: (5, -90, True)}[k]
    pts = []
    n = sides * (2 if star else 1)
    for p in range(n):
        a = math.radians(rot + 360 * p / n)
        rr = (r * 1.25 if p % 2 == 0 else r * .55) if star else r * (1.2 if sides == 3 else 1.1)
        pts.append(f"{x + rr * math.cos(a):.1f},{y + rr * math.sin(a):.1f}")
    return f'<polygon points="{" ".join(pts)}"/>'


def _bump(site: Site) -> str:
    m = site.model
    js = m.judges
    if not js:
        return ""
    cands = [c for c in m.ordered() if m.ranks(c.slug)]
    n = max(len(j.rows) for j in js)
    row_h, top, bottom = 36, 64, 20
    left, right, axis = 210, 210, 28
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
        marks = "".join(_shape(c.index, x, y(r)) for x, r in pts if r is not None)
        known = [(x, r) for x, r in pts if r is not None]
        (lx, lr), (rx, rr) = known[0], known[-1]
        labels = (f'<text class="rk-bl" x="{x0 - 16:.1f}" y="{y(lr) + 4:.1f}" text-anchor="end">{esc(c.name)}</text>'
                  f'<text class="rk-bl" x="{x0 + plot_w + 16:.1f}" y="{y(rr) + 4:.1f}">{esc(c.name)}</text>')
        parts.append(f'<g class="rk-series" style="--c:{cat(c.index)}">{lines}<g class="mk">{marks}</g>{labels}</g>')
    for c in cands:
        ranks = m.ranks(c.slug)
        desc.append(f"{c.name}: " + ", ".join(f"{j.label} {ranks.get(j.id, '–')}" for j in js))
    desc_txt = ("Rank of each candidate (1 = best, at the top) for each judge, left to right in the order "
                + ", ".join(j.label for j in js) + ". " + "; ".join(desc) + ".")
    svg = (f'<svg class="chart rk-bump" viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
           f'aria-labelledby="bump-title bump-desc" preserveAspectRatio="xMinYMin meet">'
           f'<title id="bump-title">Bump chart: each candidate’s rank across the judges</title>'
           f'<desc id="bump-desc">{esc(desc_txt)}</desc>{"".join(parts)}</svg>')
    return f"""
<section aria-labelledby="bump-h">
<h2 id="bump-h">Ranks across judges</h2>
<p>One line per candidate, from judge to judge (rank 1 at the top). Flat lines mean the judges agree; crossings are dissents. Each line is labelled at both ends and has its own marker shape, so colour is not needed to follow it. The judge × candidate matrix above is this chart’s table equivalent.</p>
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
<li><strong>Mean rank</strong> <span class="derived">derived</span> is the arithmetic mean of a candidate’s ranks over the judges that ranked it (over the judges currently shown, when you filter by material). Equal means are ties and are shown as ties: “=1” means shared first place. The place (#) is only given to candidates ranked by every judge; a candidate that some judges did not rank shows how many did (e.g. “4/5 judges”) and is listed after the others.</li>
<li><strong>Spread</strong> <span class="derived">derived</span> gives the best and worst rank a candidate received (min–max) and σ, the population standard deviation of its ranks across judges: σ = √(Σ(r − mean)² / n). A large σ marks a controversial candidate. In the glyph, each dot is one judge and the tick is the mean.</li>
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
              scripts=["rankings.js"], wide=True)

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
