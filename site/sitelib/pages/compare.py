"""compare/ — pick any two candidates and see them side by side.

compare/index.html            picker form, computed suggestions, and a no-JS list of every pair page
compare/<a>-vs-<b>/index.html one page per ordered pair a != b (the URL is the selection; swapping
                              the slugs gives the reverse pair)

Everything is discovered from the model: candidates, judges, review types and their criteria.
Quotes (judge justifications, special-elements bullets, reviewer reasons) are rendered verbatim
from the source Markdown and linked to their file. Derived values are marked as derived.
"""
from __future__ import annotations

import re
from fractions import Fraction
from itertools import combinations

from .. import md
from ..fragments import (cand_url, caveats_html, cat, cat_dash, compare_url, fmt_mean, fmt_score, judge_url, marker_svg, md_link,
                         play_url, review_url, standing_html)
from ..layout import Site, esc, figure, prompt_badge

ORDER = 400

DERIVED = '<span class="derived">derived</span>'
SHOTS_PER_SIDE = 4
MINUS = "−"
SCRIPTS = ["compare.js"]


# ---------------------------------------------------------------- small helpers

def _signed(x: float, fmt: str = "{:.0f}") -> str:
    """'+2', '−1.4', '0' — explicit sign, Unicode minus."""
    s = fmt.format(abs(x))
    if float(s) == 0:
        return s
    return ("+" if x > 0 else MINUS) + s


def _find_line(text: str, needle: str) -> int | None:
    """1-based number of the first line of text containing the first 50 chars of needle."""
    needle = needle.strip()[:50]
    if not needle:
        return None
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


def _ev(site: Site, path: str, label: str, line: int | None = None) -> str:
    return site.evidence(path, label + (f" line {line}" if line else ""), anchor=f"#L{line}" if line else "", line=line)


def _inline(site: Site, src: str, text: str) -> str:
    return md.render_inline(text, link=md_link(site, src))


def _tag(side: str, c, *, name: bool = False) -> str:
    """Side marker: a coloured bar plus the letter 'A'/'B' as text (never colour alone)."""
    nm = f' <span class="cmp-tag-name">{esc(c.label)}</span>' if name else ""
    return f'<span class="cmp-tag" style="--side:{cat(c.index)}"><span class="cmp-tag-l">{side}</span>{nm}</span>'


def _cols(a_html: str, b_html: str, a, b, cls: str = "") -> str:
    """Two side-by-side columns (stacked on phones), each labelled with its A/B marker."""
    return (f'<div class="cmp-cols {cls}">'
            f'<div class="cmp-side" style="--side:{cat(a.index)}">{a_html}</div>'
            f'<div class="cmp-side" style="--side:{cat(b.index)}">{b_html}</div></div>')


def _wrap(label: str) -> str:
    """Opening tag of a matrix scroll container (sticky header row + first column, base.css .matrix-wrap);
    focusable and named so it can be scrolled by keyboard."""
    return f'<div class="table-wrap matrix-wrap cmp-tw" tabindex="0" role="region" aria-label="{esc(label)} (scrolls)">'


def _family(folder: str) -> str | None:
    """Folder without its trailing '-v<N>' (None if it has none)."""
    m = re.fullmatch(r"(.+)-v\d+", folder)
    return m.group(1) if m else None


def _diffs(m, a, b) -> list[tuple[object, int, int]]:
    """(judge, rank of a, rank of b) for every judge that ranked both."""
    out = []
    for j in m.judges:
        r = j.rank
        if a.slug in r and b.slug in r:
            out.append((j, r[a.slug], r[b.slug]))
    return out


# ---------------------------------------------------------------- suggestions (all computed)

def suggestions(m) -> list[tuple[object, object, str, str]]:
    """(a, b, titles, reasons html) — tie pairs on mean rank, v0-vs-v1 pairs of one model family,
    and the pair the judges disagree on most. Unordered duplicates are dropped (first wins)."""
    order = {c.slug: i for i, c in enumerate(m.ordered())}
    out: list[list] = []
    seen: dict[frozenset, list] = {}

    def add(a, b, title, reason):
        """A pair suggested for several reasons is listed once, with every reason (first order wins)."""
        key = frozenset((a.slug, b.slug))
        if a.slug == b.slug:
            return
        if key in seen:
            seen[key][2].append(title)
            seen[key][3].append(reason)
            return
        seen[key] = [a, b, [title], [reason]]
        out.append(seen[key])

    # 1. candidates tied on mean rank (among those ranked by every judge)
    groups: dict[Fraction, list] = {}
    for c in m.ordered():
        if m.full(c.slug):
            groups.setdefault(m.mean_rank(c.slug), []).append(c)
    for mean, cs in groups.items():
        for a, b in combinations(cs, 2):
            add(a, b, "Tied on mean rank",
                f"Both have a mean rank of {esc(fmt_mean(mean))} {DERIVED} over all {len(m.judges)} judges.")

    # 2. same folder apart from the trailing -v<N>: one model, two prompts
    fams: dict[str, list] = {}
    for c in m.candidates:
        f = _family(c.folder)
        if f:
            fams.setdefault(f, []).append(c)
    for f, cs in sorted(fams.items(), key=lambda kv: min(order[c.slug] for c in kv[1])):
        cs = sorted(cs, key=lambda c: (c.prompt, c.index))
        for a, b in combinations(cs, 2):
            add(a, b, f"Same model, prompt {a.prompt} vs {b.prompt}",
                f"Same vendor, product, model and effort; only the prompt differs "
                f"(the folder names differ only in their trailing <code>-v…</code>). Each was judged against its own prompt.")

    # 3. biggest disagreement: widest range of per-judge rank differences (A − B)
    best = None
    for a, b in combinations(m.ordered(), 2):
        d = [ra - rb for _j, ra, rb in _diffs(m, a, b)]
        if len(d) < 2:
            continue
        rng = max(d) - min(d)
        if best is None or rng > best[0]:
            best = (rng, a, b, min(d), max(d))
    if best and best[0] > 0:
        rng, a, b, lo, hi = best
        add(a, b, "Judges disagree most",
            f"The per-judge rank difference (A − B) runs from {_signed(lo)} to {_signed(hi)}, a range of {rng} places "
            f"{DERIVED}: the widest of any pair.")
    return [(a, b, " · ".join(ts), " ".join(rs)) for a, b, ts, rs in out]


# ---------------------------------------------------------------- picker

def picker(site: Site, a=None, b=None, *, swap: bool = True) -> str:
    m = site.model

    def sel(name: str, label: str, cur) -> str:
        opts = "".join(f'<option value="{esc(c.slug)}"{" selected" if cur is not None and c.slug == cur.slug else ""}>'
                       f"{esc(c.label)}</option>" for c in m.ordered())
        return (f'<div class="cmp-field"><label for="cmp-{name}">{label}</label>'
                f'<select id="cmp-{name}" name="{name}" aria-describedby="cmp-hint">{opts}</select></div>')

    swap = (f'<a class="btn cmp-swap" href="{compare_url(b, a)}">Swap<span class="sr-only"> A and B</span>'
            f' <span aria-hidden="true">⇄</span></a>') if swap and a is not None and b is not None else ""
    return f"""<form class="cmp-picker card" method="get" autocomplete="off" action="@/compare/" data-compare-base="@/compare/" aria-label="Choose two candidates">
<div class="cmp-fields">
{sel("a", "Candidate A", a)}
{sel("b", "Candidate B", b)}
<div class="cmp-actions"><button class="btn btn-primary" type="submit">Compare</button>{swap}</div>
</div>
<p id="cmp-hint" class="small muted cmp-hint">With JavaScript on, changing a selection opens that comparison at once. Every pair has its own address, <code>compare/&lt;a&gt;-vs-&lt;b&gt;/</code>, so a comparison can be bookmarked and shared.</p>
<p class="cmp-status small" role="status" aria-live="polite" data-cmp-status></p>
</form>"""


# ---------------------------------------------------------------- index page

def build_index(site: Site) -> None:
    m = site.model
    cs = m.ordered()
    sug = suggestions(m)
    cards = "".join(
        f'<li class="card cmp-sug"><p class="cmp-sug-k">{esc(title)}</p>'
        f'<p class="cmp-sug-pair"><a href="{compare_url(a, b)}">{esc(a.label)} <span class="muted">vs</span> {esc(b.label)}</a></p>'
        f'<p class="small muted">{reason}</p></li>' for a, b, title, reason in sug)
    groups = []
    for a in cs:
        links = "".join(f'<li><a href="{compare_url(a, b)}"><span class="sr-only">{esc(a.label)} </span>vs {esc(b.label)}</a></li>'
                        for b in cs if b.slug != a.slug)
        groups.append(f'<section class="cmp-group" aria-labelledby="g-{esc(a.slug)}">'
                      f'<h3 id="g-{esc(a.slug)}"><span class="cmp-dot" style="--side:{cat(a.index)}" aria-hidden="true"></span>'
                      f'{esc(a.label)} {prompt_badge(a.prompt)}</h3><ul>{links}</ul></section>')
    n = len(cs)
    body = f"""<h1>Compare two candidates</h1>
<p class="lede">Pick any two of the {n} candidates to see them side by side: the rank every judge gave them, their
phase-1 review scores, the judges' verbatim justifications, the special elements credited to each, and screenshots.
The selection lives in the URL.</p>
{picker(site, cs[0] if cs else None, cs[1] if len(cs) > 1 else None, swap=False)}
{caveats_html(compact=True)}
<section aria-labelledby="sug-h">
<h2 id="sug-h">Suggested comparisons</h2>
<p class="small muted">Computed from the data at build time: pairs tied on mean rank, builds of the same model from
the two prompts, and the pair whose per-judge rank differences vary the most.</p>
<ul class="cmp-sugs">{cards}</ul>
</section>
<section aria-labelledby="all-h">
<h2 id="all-h">Every pair</h2>
<p class="small muted">{n * (n - 1)} comparison pages, grouped by candidate A (in mean-rank order). Each pair exists in
both directions; the reverse page swaps the columns.</p>
<div class="cmp-groups">{"".join(groups)}</div>
</section>"""
    site.page("compare/index.html", "Compare", body, section="compare", crumbs=[("Compare", "compare/")],
              scripts=SCRIPTS, description="Compare any two MandelbrotXR candidates side by side: ranks, scores, "
                                           "justifications, special elements and screenshots.")
    site.search_doc("compare/", "Compare two candidates", "page", "Compare",
                    "Compare any two candidates side by side: judge ranks, phase-1 scores, justifications, special "
                    "elements and screenshots. " + " ".join(f"{c.name} {c.label}" for c in cs)
                    + " " + " ".join(f"{t}: {a.label} vs {b.label}" for a, b, t, _r in sug))


# ---------------------------------------------------------------- pair page sections

def _card(site: Site, side: str, c) -> str:
    m = site.model
    th = c.thumbnail
    thumb = (f'<a class="cmp-thumb" href="{cand_url(c)}" tabindex="-1" aria-hidden="true">'
             f'{figure(site, th, cls="shot", link=False)}</a>') if th else \
        '<div class="cmp-thumb cmp-thumb-none" aria-hidden="true"><span>No screenshot</span></div>'
    if m.standing().get(c.slug):
        rank = (f'<dl class="cmp-stats"><div><dt>Standing</dt><dd>{standing_html(m, c)}</dd></div>'
                f'<div><dt>Mean rank {DERIVED}</dt><dd>{esc(fmt_mean(m.mean_rank(c.slug)))}</dd></div></dl>')
    else:
        rank = f'<p class="small muted">{standing_html(m, c)}</p>'
    return f"""<article class="cmp-card">
<p class="cmp-side-h">{_tag(side, c)}<span class="sr-only">Candidate {side}:</span></p>
{thumb}
<h3 class="cmp-name"><a href="{cand_url(c)}">{esc(c.name)}</a> {prompt_badge(c.prompt)}</h3>
<p class="small muted cmp-sub">{esc(c.vendor)} · {esc(c.product)}</p>
{rank}
<p class="cmp-btns"><a class="btn btn-primary" href="{play_url(c)}">Play<span class="sr-only"> {esc(c.label)}</span></a>
<a class="btn" href="{cand_url(c)}">Candidate page<span class="sr-only">: {esc(c.label)}</span></a></p>
</article>"""


def _overview(site: Site, a, b) -> str:
    m = site.model
    out = _cols(_card(site, "A", a), _card(site, "B", b), a, b, "cmp-cards")
    if a.prompt != b.prompt:
        out += (f'<p class="caveat cmp-prompt-note"><strong>Different prompts.</strong> A was built from prompt '
                f'{prompt_badge(a.prompt)} and B from prompt {prompt_badge(b.prompt)}: different prompts; each was judged '
                f'against its own. <a href="@/methodology/#prompts">Read both prompts</a>.</p>')
    full = m.full(a.slug) and m.full(b.slug)
    note = ("" if full else " A candidate not ranked by every judge has a mean that is not comparable with the others'.")
    out += (f'<p class="small muted">Mean rank {DERIVED} is the arithmetic mean of the ranks a candidate received '
            f'(1 = best); the standing counts candidates with a strictly lower mean, so ties share a place.{note} '
            f'<a href="@/methodology/#caveats">Caveats</a>.</p>')
    return out


def _th_side(side: str, c) -> str:
    return f'<th scope="col" class="num">{_tag(side, c)}<span class="cmp-th-name">{esc(c.label)}</span></th>'


def _higher(d: float, unit: str = "place") -> str:
    """Who is better when d = A − B on a lower-is-better rank scale."""
    if d == 0:
        return "tie"
    n = abs(d)
    who = "A" if d < 0 else "B"
    return f"<strong>{who}</strong> by {n:g}<span class=\"cmp-unit\"> {unit}{'s' if n != 1 else ''}</span>"


def _ranks(site: Site, a, b) -> str:
    m = site.model
    rows = []
    ca = cb = ct = 0
    for j in m.judges:
        ra, rb = j.rank.get(a.slug), j.rank.get(b.slug)
        n = len(j.rows)
        fa = f"{ra}<span class=\"muted cmp-of\"> / {n}</span>" if ra else '<span class="muted">–</span>'
        fb = f"{rb}<span class=\"muted cmp-of\"> / {n}</span>" if rb else '<span class="muted">–</span>'
        if ra and rb:
            d = ra - rb
            ca += d < 0
            cb += d > 0
            ct += d == 0
            dc, hc = _signed(d), _higher(d)
        else:
            dc, hc = "–", '<span class="muted">not ranked by this judge</span>' if not (ra or rb) else '<span class="muted">–</span>'
        mat = "browser" if j.browser else "static"
        rows.append(f'<tr><th scope="row"><a href="{judge_url(j)}">{esc(j.label)}</a> <span class="cmp-mat">{mat}</span></th>'
                    f'<td class="num">{fa}</td><td class="num">{fb}</td><td class="num">{dc}</td><td>{hc}</td></tr>')
    ma, mb = m.mean_rank(a.slug), m.mean_rank(b.slug)
    if ma is not None and mb is not None:
        dm = float(ma) - float(mb)
        dm_s = _signed(round(dm, 1), "{:.1f}")
        hm = "tie" if f"{float(ma):.1f}" == f"{float(mb):.1f}" else _higher(float(f"{dm:.1f}"))
    else:
        dm_s, hm = "–", '<span class="muted">–</span>'
    rows.append(f'<tr class="cmp-derived"><th scope="row">Mean rank {DERIVED}</th>'
                f'<td class="num"><strong>{esc(fmt_mean(ma))}</strong></td><td class="num"><strong>{esc(fmt_mean(mb))}</strong></td>'
                f'<td class="num">{dm_s}</td><td>{hm}</td></tr>')

    def sp(c):
        s = m.spread(c.slug)
        if not s:
            return "–"
        rng = f"{s[0]}" if s[0] == s[1] else f"{s[0]}–{s[1]}"
        return f'{rng}<span class="cmp-sig"> · σ {s[2]:.2f}</span>'
    rows.append(f'<tr class="cmp-derived"><th scope="row">Spread {DERIVED}</th>'
                f'<td class="num">{sp(a)}</td><td class="num">{sp(b)}</td><td class="num"></td>'
                f'<td></td></tr>')
    both = ca + cb + ct
    summary = (f"<p><strong>{both}</strong> of {len(m.judges)} judges ranked both. "
               f"A ranked higher with <strong>{ca}</strong>, B with <strong>{cb}</strong>"
               + (f", tied with <strong>{ct}</strong>" if ct else "") + ".</p>") if both else \
        "<p>No judge ranked both candidates, so their ranks cannot be compared judge by judge.</p>"
    return f"""{summary}
{_wrap("Ranks of A and B by judge")}<table class="cmp-table">
<caption class="sr-only">Rank given by each blind judge to A and B (1 = best)</caption>
<thead><tr><th scope="col">Judge</th>{_th_side("A", a)}{_th_side("B", b)}<th scope="col" class="num"><span class="cmp-long">Difference</span><span class="cmp-short" aria-hidden="true">Diff.</span><br><span class="small muted">A − B</span></th><th scope="col">Ranked higher</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p class="small muted">Rank given by each blind judge (1 = best, out of the number of candidates it ranked). Difference =
A's rank minus B's; a negative difference means A was ranked higher. Mean rank {DERIVED} = arithmetic mean of a
candidate's judge ranks; spread {DERIVED} = lowest–highest rank and the population standard deviation σ. Ranks are
quoted from each judge's <code>RANKING.md</code>, linked under Justifications.</p>"""


def _mirror_chart(m, a, b) -> str:
    """Mirrored horizontal bars of the phase-1 overall scores: A grows left, B grows right (0–10).
    Each side is labelled directly (A top left, B below it on the right, each with its series marker);
    the viewBox stays narrow so the text keeps its size on a 390 px screen."""
    types = m.review_types
    W, half, top, row = 360, 130, 52, 34
    cx = W / 2
    sc = half / 10
    H = top + len(types) * row + 22
    cid = f"mir-{a.slug}-{b.slug}"
    desc = "; ".join(
        f"{label}: A {fmt_score(m.review(t, a.slug).overall) if m.review(t, a.slug) else 'no review'}, "
        f"B {fmt_score(m.review(t, b.slug).overall) if m.review(t, b.slug) else 'no review'}" for t, _f, label in types)
    p = [f'<svg class="chart cmp-mirror" viewBox="0 0 {W} {H}" role="img" aria-labelledby="{cid}-t {cid}-d">',
         f'<title id="{cid}-t">Phase-1 overall scores out of 10: A ({esc(a.label)}) left, B ({esc(b.label)}) right</title>',
         f'<desc id="{cid}-d">{esc(desc)}</desc>',
         marker_svg(a.index, 6, 10, extra=' class="cmp-mk"'),
         f'<text class="cmp-mh" x="16" y="15" text-anchor="start">A · {esc(a.label)}</text>',
         marker_svg(b.index, W - 6, 30, extra=' class="cmp-mk"'),
         f'<text class="cmp-mh" x="{W - 16}" y="35" text-anchor="end">B · {esc(b.label)}</text>']
    base = top + len(types) * row
    for t in (0, 5, 10):
        for sgn in ((-1, 1) if t else (1,)):
            x = cx + sgn * t * sc
            p.append(f'<line class="grid-line" x1="{x:.1f}" y1="{top - 6}" x2="{x:.1f}" y2="{base}"/>')
            p.append(f'<text class="label-muted" x="{x:.1f}" y="{base + 15}" text-anchor="middle">{t}</text>')
    for i, (t, _f, label) in enumerate(types):
        y = top + i * row
        p.append(f'<text class="cmp-ml" x="{cx}" y="{y + 9}" text-anchor="middle">{esc(label)}</text>')
        for side, c, sgn in (("A", a, -1), ("B", b, 1)):
            r = m.review(t, c.slug)
            if not r:
                p.append(f'<text class="label-muted" x="{cx + sgn * 6:.1f}" y="{y + 26}" '
                         f'text-anchor="{"end" if sgn < 0 else "start"}">–</text>')
                continue
            w = max(0.0, min(10.0, r.overall)) * sc
            x = cx - w if sgn < 0 else cx
            p.append(f'<rect class="cmp-bar" x="{x:.1f}" y="{y + 14}" width="{w:.1f}" height="14" rx="2" style="fill:{cat(c.index)}'
                     + (f';stroke-dasharray:{cat_dash(c.index)}' if cat_dash(c.index) else "") + '"/>')
            tx = cx + sgn * (w + 5)
            p.append(f'<text class="cmp-mv" x="{tx:.1f}" y="{y + 25}" text-anchor="{"end" if sgn < 0 else "start"}">'
                     f'{esc(fmt_score(r.overall))}</text>')
    p.append(f'<line class="axis" x1="{cx}" y1="{top - 6}" x2="{cx}" y2="{base}"/>')
    p.append("</svg>")
    return "".join(p)


def _crit_rows(ra, rb) -> list[tuple[str, object, object]]:
    """(row label, criterion of A or None, criterion of B or None). Same count → aligned by position
    (the label shows both names when they differ); otherwise matched by name."""
    ca, cb = (ra.criteria if ra else []), (rb.criteria if rb else [])
    if ca and cb and len(ca) == len(cb):
        return [(x.name if x.name == y.name else f"{x.name} / {y.name}", x, y) for x, y in zip(ca, cb)]
    names = [c.name for c in ca] + [c.name for c in cb if c.name not in {x.name for x in ca}]
    da, db = {c.name: c for c in ca}, {c.name: c for c in cb}
    return [(n, da.get(n), db.get(n)) for n in names]


def _reasons(site: Site, side: str, c, r) -> str:
    if not r:
        return f'<p class="cmp-side-h">{_tag(side, c, name=True)}</p><p class="muted small">No review.</p>'
    src = r.files.get("REVIEW.md", r.dir)
    first = _find_line(r.md, r.criteria[0].reason) if r.criteria else None
    last = _find_line(r.md, r.criteria[-1].reason) if r.criteria else None
    lis = "".join(f'<li><strong>{esc(cr.name)}</strong> <span class="num">{esc(fmt_score(cr.score))}</span> — '
                  f'{_inline(site, src, cr.reason)}</li>' for cr in r.criteria)
    lines = f"lines {first}–{last}" if first and last and last != first else (f"line {first}" if first else "")
    label = "REVIEW.md" + (f" {lines}" if lines else "")
    ev = site.evidence(src, label, anchor=f"#L{first}" if first else "", line=first)
    return (f'<p class="cmp-side-h">{_tag(side, c, name=True)}</p>'
            f'<blockquote class="quote cmp-reasons"><ul>{lis}</ul>'
            f'<cite>{esc(r.type_label)} review (blind id <code>{esc(r.blind_id)}</code>), criteria table, verbatim — {ev}</cite></blockquote>')


def _scores(site: Site, a, b) -> str:
    m = site.model
    if not m.review_types:
        return '<p class="muted">No phase-1 review types exist.</p>'
    rows = []
    for t, _f, label in m.review_types:
        ra, rb = m.review(t, a.slug), m.review(t, b.slug)
        fa = f'<a href="{review_url(ra)}">{esc(fmt_score(ra.overall))}</a>' if ra else '<span class="muted">–</span>'
        fb = f'<a href="{review_url(rb)}">{esc(fmt_score(rb.overall))}</a>' if rb else '<span class="muted">–</span>'
        if ra and rb:
            d = ra.overall - rb.overall
            dc = _signed(d, "{:g}")
            hc = "tie" if d == 0 else f"<strong>{'A' if d > 0 else 'B'}</strong> by {abs(d):g}"
        else:
            dc, hc = "–", '<span class="muted">–</span>'
        rows.append(f'<tr><th scope="row">{esc(label)}</th><td class="num">{fa}</td><td class="num">{fb}</td>'
                    f'<td class="num">{dc}</td><td>{hc}</td></tr>')
    out = [f"""<p>Each phase-1 reviewer scored one candidate at a time, blind, on six 1–10 criteria of its own review type,
plus an overall score. Higher is better. Scores link to the full review.</p>
<figure class="cmp-fig">{_mirror_chart(m, a, b)}<figcaption class="small muted">Overall score per review type, mirrored:
A to the left of the centre line, B to the right. The same numbers are in the table below.</figcaption></figure>
{_wrap("Phase-1 overall scores of A and B")}<table class="cmp-table">
<caption>Phase-1 overall score of each blind review (1–10, higher is better). Difference = A − B.</caption>
<thead><tr><th scope="col">Review</th>{_th_side("A", a)}{_th_side("B", b)}<th scope="col" class="num"><span class="cmp-long">Difference</span><span class="cmp-short" aria-hidden="true">Diff.</span><br><span class="small muted">A − B</span></th><th scope="col">Scored higher</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>"""]
    for t, _f, label in m.review_types:
        ra, rb = m.review(t, a.slug), m.review(t, b.slug)
        if not ra and not rb:
            continue
        crow = []
        for name, x, y in _crit_rows(ra, rb):
            sx = esc(fmt_score(x.score)) if x else '<span class="muted">–</span>'
            sy = esc(fmt_score(y.score)) if y else '<span class="muted">–</span>'
            dc = _signed(x.score - y.score, "{:g}") if x and y else "–"
            crow.append(f'<tr><th scope="row">{esc(name)}</th><td class="num">{sx}</td><td class="num">{sy}</td><td class="num">{dc}</td></tr>')
        tid = esc(t.replace("_", "-"))
        out.append(f"""<section class="cmp-sub-sec" aria-labelledby="crit-{tid}">
<h3 id="crit-{tid}">{esc(label)} review criteria</h3>
{_wrap(f"{label} review criteria of A and B")}<table class="cmp-table cmp-crit">
<caption>{esc(label)} review: criterion scores (1–10). Difference = A − B. Criteria are specific to this review type.</caption>
<thead><tr><th scope="col">Criterion</th>{_th_side("A", a)}{_th_side("B", b)}<th scope="col" class="num"><span class="cmp-long">Difference</span><span class="cmp-short" aria-hidden="true">Diff.</span><br><span class="small muted">A − B</span></th></tr></thead>
<tbody>{"".join(crow)}</tbody></table></div>
<details class="fold cmp-fold"><summary>The reviewers' one-line reasons, verbatim</summary>
{_cols(_reasons(site, "A", a, ra), _reasons(site, "B", b, rb), a, b)}
</details>
</section>""")
    return "\n".join(out)


def _just_side(site: Site, side: str, c, j) -> str:
    row = next((r for r in j.rows if r.slug == c.slug), None)
    head = f'<p class="cmp-side-h">{_tag(side, c, name=True)}</p>'
    if not row:
        return head + '<p class="muted small">Not ranked by this judge.</p>'
    p = j.files["RANKING.md"]
    line = _find_line(j.md, row.justification)
    return (head + f'<p class="small muted cmp-rk">Rank <strong>{row.rank}</strong> of {len(j.rows)} · '
            f'seen as letter <strong class="cmp-letter">{esc(row.letter)}</strong></p>'
            f'<blockquote class="quote"><p>{_inline(site, p, row.justification)}</p>'
            f'<cite>{esc(j.label)} judge, justification for {esc(row.letter)}, verbatim — {_ev(site, p, "RANKING.md", line)}</cite>'
            f'</blockquote>')


def _justifications(site: Site, a, b) -> str:
    m = site.model
    items = []
    for j in m.judges:
        mat = "hands-on in a browser" if j.browser else "static material"
        items.append(f'<article class="cmp-judge"><h3><a href="{judge_url(j)}">{esc(j.label)} judge</a> '
                     f'<span class="muted small">· {mat}</span></h3>'
                     f'{_cols(_just_side(site, "A", a, j), _just_side(site, "B", b, j), a, b)}</article>')
    return ("<p>Each judge ranked every candidate under its own shuffled letters, without names, and wrote a short "
            "justification per rank. Quoted verbatim from the judge's <code>RANKING.md</code>.</p>" + "".join(items))


def _special_item(site: Site, j, s, a, b) -> str:
    m = site.model
    p = j.files["RANKING.md"]
    line = _find_line(j.md, s.raw)
    who = []
    for L, sl in zip(s.letters, s.slugs):
        if sl == a.slug:
            who.append(f'<span class="cmp-letter">{esc(L)}</span> = {_tag("A", a)}')
        elif sl == b.slug:
            who.append(f'<span class="cmp-letter">{esc(L)}</span> = {_tag("B", b)}')
        else:
            o = m.cand(sl)
            who.append(f'<span class="cmp-letter">{esc(L)}</span> = <a href="{cand_url(o)}">{esc(o.label)}</a>')
    return (f'<li><blockquote class="quote"><p>{_inline(site, p, s.raw)}</p>'
            f'<cite><a href="{judge_url(j)}">{esc(j.label)} judge</a> · {"; ".join(who)} — {_ev(site, p, "RANKING.md", line)}</cite>'
            f'</blockquote></li>')


def _specials(site: Site, a, b) -> str:
    m = site.model
    only_a, only_b, shared = [], [], []
    for j in m.judges:
        for s in j.special:
            ia, ib = a.slug in s.slugs, b.slug in s.slugs
            if ia and ib:
                shared.append(_special_item(site, j, s, a, b))
            elif ia:
                only_a.append(_special_item(site, j, s, a, b))
            elif ib:
                only_b.append(_special_item(site, j, s, a, b))

    def block(side, c, items):
        n = len(items)
        head = (f'<p class="cmp-side-h">{_tag(side, c, name=True)} <span class="muted small">{n} bullet{"s" if n != 1 else ""} '
                f'credit {side} only</span></p>')
        return head + (f'<ul class="cmp-quotes">{"".join(items)}</ul>' if items else
                       '<p class="muted small">No bullet credits this candidate without the other.</p>')
    sh = (f'<ul class="cmp-quotes">{"".join(shared)}</ul>' if shared else
          '<p class="muted small">No bullet credits both candidates.</p>')
    return (f"<p>Bullets from the judges' “Special elements” sections, quoted verbatim. Letters are each judge's blind "
            f"labels; a bullet may also name other candidates. Every element, grouped by technique, is in the "
            f'<a href="@/techniques/">techniques catalog</a>.</p>'
            + _cols(block("A", a, only_a), block("B", b, only_b), a, b)
            + f'<h3 class="cmp-shared-h">Shared <span class="muted small">{len(shared)} bullet{"s" if len(shared) != 1 else ""} '
              f'credit both A and B</span></h3>' + sh)


def _pick_shots(c, n: int) -> list:
    """Up to n screenshots, round-robin over who took them (keeps the source order)."""
    groups: dict[str, list] = {}
    for s in c.shots:
        groups.setdefault(s.source_id, []).append(s)
    out, i = [], 0
    while len(out) < n and any(i < len(g) for g in groups.values()):
        for g in groups.values():
            if i < len(g) and len(out) < n:
                out.append(g[i])
        i += 1
    return out


def _shots_side(site: Site, side: str, c) -> str:
    shots = _pick_shots(c, SHOTS_PER_SIDE)
    head = f'<p class="cmp-side-h">{_tag(side, c, name=True)}</p>'
    if not shots:
        return head + '<p class="muted small">No screenshots were taken of this candidate.</p>'
    figs = "".join(figure(site, s) for s in shots)
    total = len(c.shots)
    more = (f'<p class="small"><a href="{cand_url(c)}#screenshots">All {total} screenshot{"s" if total != 1 else ""} '
            f'of {esc(c.label)}</a> on the candidate page, with their verbatim captions.</p>')
    return head + f'<div class="gallery cmp-gallery">{figs}</div>' + more


def _screens(site: Site, a, b) -> str:
    return (f"<p>Up to {SHOTS_PER_SIDE} screenshots per candidate, taken in desktop Chrome by the browser reviewers and "
            f"browser judges (one from each source in turn).</p>"
            + _cols(_shots_side(site, "A", a), _shots_side(site, "B", b), a, b))


def build_pair(site: Site, a, b) -> None:
    sections = [
        ("overview", "The two candidates", _overview(site, a, b)),
        ("ranks", "Ranks", _ranks(site, a, b)),
        ("scores", "Phase-1 scores", _scores(site, a, b)),
        ("justifications", "Justifications", _justifications(site, a, b)),
        ("special", "Special elements", _specials(site, a, b)),
        ("screenshots", "Screenshots", _screens(site, a, b)),
    ]
    toc = "".join(f'<li><a href="#{sid}">{esc(t)}</a></li>' for sid, t, _ in sections)
    secs = "\n".join(f'<section id="{sid}" class="cmp-sec" aria-labelledby="{sid}-h"><h2 id="{sid}-h">{esc(t)}</h2>\n{h}\n</section>'
                     for sid, t, h in sections)
    body = f"""<h1 class="cmp-h1"><span class="cmp-h1-k">Compare</span> {_tag("A", a)} {esc(a.name)} <span class="muted cmp-vs">vs</span> {_tag("B", b)} {esc(b.name)}</h1>
{picker(site, a, b)}
<nav class="cmp-toc" aria-label="On this page"><ol>{toc}</ol></nav>
{secs}"""
    site.page(f"compare/{a.slug}-vs-{b.slug}/index.html", f"{a.name} vs {b.name}", body, section="compare",
              crumbs=[("Compare", "compare/"), (f"{a.label} vs {b.label}", f"compare/{a.slug}-vs-{b.slug}/")],
              scripts=SCRIPTS,
              description=f"{a.name} vs {b.name}: judge ranks, phase-1 scores, verbatim justifications, special "
                          f"elements and screenshots side by side.")


def build(site: Site) -> None:
    build_index(site)
    cs = site.model.ordered()
    for a in cs:
        for b in cs:
            if a.slug != b.slug:
                build_pair(site, a, b)
