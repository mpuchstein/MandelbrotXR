"""Candidate pages: candidates/ (overview cards) and candidates/<slug>/ (one page per candidate).

Everything is driven by the model (site/sitelib/data.py): candidates, judges, review types and
their criteria are discovered, never hardcoded. Quotes are rendered verbatim from the source
Markdown and linked to their file (local copy + GitHub at the build commit).
"""
from __future__ import annotations

import os
import re

from .. import md, qr
from ..fragments import (cand_url, cat, compare_url, find_line, fmt_mean, fmt_score, inline, judge_url, line_html,
                         play_url, review_url, standing_html, title_badge)
from ..layout import Site, esc, figure, prompt_badge

ORDER = 300

DERIVED = '<span class="derived">derived</span>'

# Warning detectors: which lines of the reviews / rankings speak about a scanned fact.
EXTERNAL_RE = re.compile(r"\bCDNs?\b|cdn\.|cdnjs|tailwind|\br128\b|offline|network|Google Fonts|fonts\.googleapis", re.I)
ALERT_RE = re.compile(r"alert\(|native dialog|native `?alert", re.I)
PROCESS_DOCS = ("Judge/README.md", "ReviewOrchestrator/README.md")


# ---------------------------------------------------------------- small helpers

def _read(site: Site, path: str) -> str:
    with open(os.path.join(site.repo, path), encoding="utf-8") as f:
        return f.read()


def _ev(site: Site, path: str, label: str, line: int | None = None) -> str:
    return site.evidence(path, label, anchor=f"#L{line}" if line else "", line=line)


def _blind_ids(site: Site, slug: str) -> list[str]:
    return [nn for nn, s in sorted(site.model.blind.items()) if s == slug]


def _letter(j, slug: str) -> str | None:
    return next((r.letter for r in j.rows if r.slug == slug), None)


def _mean_html(site: Site, c) -> str:
    m = site.model.mean_rank(c.slug)
    return esc(fmt_mean(m))


def _how_mean(site: Site, c) -> str:
    n = len(site.model.ranks(c.slug))
    return f"arithmetic mean of the {n} judge rank{'s' if n != 1 else ''} this candidate received"


def _score_list(site: Site, c, cls: str = "scores") -> str:
    items = []
    for tid, _folder, label in site.model.review_types:
        r = site.model.review(tid, c.slug)
        val = f"{esc(fmt_score(r.overall))}<span class=\"of\">/10</span>" if r else '<span class="muted">–</span>'
        items.append(f"<div><dt>{esc(label)}</dt><dd>{val}</dd></div>")
    return f'<dl class="{cls}">{"".join(items)}</dl>'


# ---------------------------------------------------------------- charts

def _label_link(c) -> str:
    """Short candidate label (tables, charts, cross-references); Candidate.name is for this page's heading."""
    return f'<a href="{cand_url(c)}">{esc(c.label)}</a>'


def _bar_path(x0: float, by: float, w: float, bh: float) -> str:
    """Bar from x0, w long, bh high, rounded at its outer end only."""
    r = min(4.0, w, bh / 2)
    return (f"M{x0:.1f} {by:.1f}h{w - r:.1f}a{r:.1f} {r:.1f} 0 0 1 {r:.1f} {r:.1f}v{bh - 2 * r:.1f}"
            f"a{r:.1f} {r:.1f} 0 0 1 -{r:.1f} {r:.1f}h-{w - r:.1f}z")


def _bar_chart(review, c, wide: bool) -> str:
    """Horizontal bar chart (0–10) of one review's criteria, drawn at its display size so text stays 1:1.
    wide: criterion labels in a left gutter, bars across the content column (shown from 48rem);
    narrow: labels above each bar (phones). Bars use the candidate's fixed series colour; every bar
    carries its criterion name and value as text. Gridlines never cross a label."""
    n = len(review.criteria)
    if wide:
        longest = max((len(cr.name) for cr in review.criteria), default=8)
        gut = min(300, max(120, round(longest * 7.6) + 20))
        W, row, top, bh, end = 720, 34, 4, 18, 34
    else:
        gut, W, row, top, bh, end = 0, 360, 42, 6, 13, 28
    scale = (W - gut - end) / 10
    H = top + n * row + 22
    tid = f"chart-{review.type_id}-{review.slug}-{'w' if wide else 'n'}"
    parts = [f'<svg class="chart crit-chart {"crit-wide" if wide else "crit-narrow"}" viewBox="0 0 {W} {H}" role="img" '
             f'aria-labelledby="{tid}-t {tid}-d" preserveAspectRatio="xMinYMin meet" style="--key:{cat(c.index)}">',
             f'<title id="{tid}-t">{esc(review.type_label)} review of {esc(c.label)}: criterion scores, 0–10</title>',
             f'<desc id="{tid}-d">' + esc("; ".join(f"{cr.name}: {fmt_score(cr.score)}" for cr in review.criteria)) + "</desc>"]
    base_y = top + n * row
    for t in range(0, 11, 2):
        x = round(gut + t * scale, 1)
        if wide:
            parts.append(f'<line class="grid-line" x1="{x}" y1="{top}" x2="{x}" y2="{base_y}"/>')
        else:   # one short segment per bar band, so the labels above the bars stay clear
            for i in range(n):
                by = top + i * row + 21
                parts.append(f'<line class="grid-line" x1="{x}" y1="{by - 3}" x2="{x}" y2="{by + bh + 3}"/>')
        anchor = "start" if t == 0 and not wide else "middle"
        parts.append(f'<text class="label-muted tick" x="{x}" y="{base_y + 16}" text-anchor="{anchor}">{t}</text>')
    for i, cr in enumerate(review.criteria):
        y = top + i * row
        w = max(0.0, min(10.0, cr.score)) * scale
        by = y + (row - bh) / 2 if wide else y + 21
        ly = by + bh / 2 + 5 if wide else y + 15
        path = _bar_path(gut, by, w, bh) if w > 0 else ""
        parts.append(f'<g class="bar-row"><title>{esc(cr.name)}: {esc(fmt_score(cr.score))} / 10</title>'
                     f'<rect class="hit" x="0" y="{y}" width="{W}" height="{row}"/>'
                     f'<text class="crit-label" x="0" y="{ly:.1f}">{esc(cr.name)}</text>'
                     + (f'<path class="bar" d="{path}"/>' if path else "")
                     + f'<text class="crit-val" x="{gut + w + 6:.1f}" y="{by + bh / 2 + 5:.1f}">{esc(fmt_score(cr.score))}</text></g>')
    parts.append(f'<line class="axis" x1="{gut}" y1="{top}" x2="{gut}" y2="{base_y}"/>')
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------- index page

def _card(site: Site, c) -> str:
    m = site.model
    th = c.thumbnail
    if th:
        thumb = figure(site, th, cls="shot cand-thumb", link=False)
        thumb = f'<a class="thumb-link" href="{cand_url(c)}" tabindex="-1" aria-hidden="true">{thumb}</a>'
    else:
        thumb = '<div class="cand-thumb placeholder" aria-hidden="true"><span>No screenshot</span></div>'
    st = m.standing().get(c.slug)
    if st:
        rank_line = (f'<p class="cand-rank"><span class="big">{_mean_html(site, c)}</span> mean rank'
                     f'<br><span class="muted small">standing {standing_html(m, c)}</span></p>')
    elif m.ranks(c.slug):  # ranked by some judges only: its mean is not comparable (as on the compare page)
        rank_line = f'<p class="cand-rank muted">{standing_html(m, c)}</p>'
    else:
        rank_line = '<p class="cand-rank muted">not ranked by any judge</p>'
    return f"""<article class="card cand-card">
{thumb}
<div class="cand-card-body">
<h2 class="cand-title"><span class="cand-key" style="--key:{cat(c.index)}" aria-hidden="true"></span><a href="{cand_url(c)}">{esc(c.label)}</a>{title_badge(c)}</h2>
<p class="muted small cand-sub">{esc(c.vendor)} · {esc(c.product)}</p>
{rank_line}
<p class="small muted scores-head">Phase-1 overall scores</p>
{_score_list(site, c)}
<p class="cand-actions"><a class="btn btn-play-sec" href="{play_url(c)}"><span class="play-icon" aria-hidden="true"></span>Play<span class="sr-only"> {esc(c.label)}</span></a>
<a class="btn" href="{cand_url(c)}">Details<span class="sr-only"> on {esc(c.label)}</span></a></p>
</div>
</article>"""


def build_index(site: Site) -> None:
    m = site.model
    cards = "\n".join(_card(site, c) for c in m.ordered())
    judges = len(m.judges)
    body = f"""<h1>Candidates</h1>
<p class="lede">{len(m.candidates)} standalone WebXR Mandelbrot pages, each built by an AI coding assistant from one of
the task prompts. They are listed by mean rank across the {judges} blind judges. Every card links to a page with
the product, its reviews, every judge's verbatim justification, screenshots and facts.</p>
<p class="note small"><strong>Mean rank</strong> {DERIVED} (on every card below) is the arithmetic mean of a candidate's ranks over the judges
that ranked it. Standing = 1 + the number of candidates with a strictly lower mean rank, among those ranked by
every judge (a competition rank: ties share a place, e.g. 1, 1, 3; shown as “(tie)”). Phase-1 overall scores are the 1–10 scores the blind reviewers wrote, one per review type.
<a href="@/rankings/">Full rankings</a> · <a href="@/methodology/#caveats">caveats</a>.</p>
<div class="grid cand-grid">
{cards}
</div>"""
    site.page("candidates/index.html", "Candidates", body, section="candidates", crumbs=[("Candidates", "candidates/")],
              description="All MandelbrotXR candidates with mean rank, phase-1 scores and a Play button.")
    site.search_doc("candidates/", "Candidates", "page", "Candidates",
                    " ".join(f"{c.name} {c.vendor} {c.product} {c.model}" for c in m.candidates))


# ---------------------------------------------------------------- candidate page sections

def _header(site: Site, c) -> str:
    m = site.model
    st = m.standing().get(c.slug)
    if st:
        rank = (f'<p class="cand-standing"><span class="stat"><span class="stat-k">Standing</span> '
                f'<span class="stat-v">{standing_html(m, c)}</span></span> '
                f'<span class="stat"><span class="stat-k">Mean rank</span> <span class="stat-v">{_mean_html(site, c)}</span> {DERIVED}</span>'
                f'<span class="muted small how">{esc(_how_mean(site, c))}; ties share a place.</span></p>')
    elif m.ranks(c.slug):
        n, total = m.coverage(c.slug)
        rank = f'<p class="cand-standing muted">Ranked by {n} of {total} judges; a standing needs a rank from every judge.</p>'
    else:
        rank = '<p class="cand-standing muted">Not ranked by any judge.</p>'
    return f"""<header class="cand-head">
<p class="eyebrow">Candidate</p>
<h1>{esc(c.label)}</h1>
<p class="cand-meta">{esc(c.vendor)} · {esc(c.product)} · <a class="badge-link" href="@/methodology/#prompts" title="Read prompt {esc(c.prompt)} on the methodology page">{prompt_badge(c.prompt)} <span class="small">prompt</span></a></p>
{rank}
<div class="play-row">
<a class="btn btn-primary btn-play" href="{play_url(c)}"><span class="play-icon" aria-hidden="true"></span>Play {esc(c.label)}</a>
<a class="btn" href="{esc(site.gh(c.html_path))}" rel="noopener">Source on GitHub<span class="sr-only"> ({esc(c.product_file)})</span></a>
</div>
<p class="small muted play-note">Play opens the product full-page; WebXR needs a top-level page, so it is not embedded here.</p>
</header>"""


def _review_lines(site: Site, c, rx: re.Pattern) -> list[tuple[str, str, int, str]]:
    """(label, path, line number, html) for each matching line of this candidate's REVIEW.md files."""
    out = []
    for tid, _f, label in site.model.review_types:
        r = site.model.review(tid, c.slug)
        if not r or "REVIEW.md" not in r.files:
            continue
        p = r.files["REVIEW.md"]
        for i, line in enumerate(r.md.splitlines(), 1):
            if line.strip() and rx.search(line):
                out.append((f"{label} review", p, i, line_html(site, p, line)))
    return out


def _judge_lines(site: Site, c, rx: re.Pattern) -> list[tuple[str, str, int | None, str]]:
    out = []
    for j in site.model.judges:
        p = j.files["RANKING.md"]
        for row in j.rows:
            if row.slug == c.slug and rx.search(row.justification):
                out.append((f"{j.label} judge, justification (letter {row.letter})", p,
                            find_line(j.md, row.justification), inline(site, p, row.justification)))
        for s in j.special:
            if c.slug in s.slugs and rx.search(s.raw):
                out.append((f"{j.label} judge, special element", p, find_line(j.md, s.raw), inline(site, p, s.raw)))
    return out


def _process_lines(site: Site, c, rx: re.Pattern) -> list[tuple[str, str, int, str]]:
    """Lines of the process READMEs that name this candidate (folder or phase-1 blind id) and match rx."""
    ids = [c.folder] + _blind_ids(site, c.slug)
    pat = re.compile("|".join(rf"(?<![\w-]){re.escape(x)}(?![\w-])" for x in ids))
    out = []
    for p in PROCESS_DOCS:
        if not os.path.isfile(os.path.join(site.repo, p)):
            continue
        for i, line in enumerate(_read(site, p).splitlines(), 1):
            if pat.search(line) and rx.search(line):
                out.append((p, p, i, line_html(site, p, line)))
    return out


def _quotes(site: Site, items) -> str:
    lis = []
    for label, path, line, html in items:
        lis.append(f'<li><blockquote class="q-line"><p>{html}</p>'
                   f'<cite>{esc(label)} — {_ev(site, path, os.path.basename(path) + (f" line {line}" if line else ""), line)}</cite>'
                   f"</blockquote></li>")
    return f'<ul class="quote-list">{"".join(lis)}</ul>'


def _quote_block(site: Site, items) -> str:
    """The first matching line of every source is shown; the remaining lines sit in a fold."""
    if not items:
        return '<p class="small muted">No line of this candidate\'s reviews or rankings mentions it.</p>'
    first, rest, seen = [], [], set()
    for it in items:
        key = (it[0].split(",")[0], it[1])
        (rest if key in seen else first).append(it)
        seen.add(key)
    srcs = len(seen)
    out = (f'<p class="small q-intro">What the reviews and judges wrote, verbatim: {len(items)} matching '
           f'line{"s" if len(items) != 1 else ""} from {srcs} source{"s" if srcs != 1 else ""}; the first from each source is shown.</p>'
           + _quotes(site, first))
    if rest:
        out += (f'<details class="fold q-more"><summary>{len(rest)} more verbatim line{"s" if len(rest) != 1 else ""}</summary>'
                f'{_quotes(site, rest)}</details>')
    return out


def _warnings(site: Site, c) -> str:
    blocks = []
    if c.external:
        urls = "".join(f"<li><code>{esc(u)}</code></li>" for u in c.external)
        items = _review_lines(site, c, EXTERNAL_RE) + _judge_lines(site, c, EXTERNAL_RE) + _process_lines(site, c, EXTERNAL_RE)
        n = len(c.external)
        q = _quote_block(site, items)
        blocks.append(f"""<div class="caveat warn">
<h3>Loads {n} external resource{"s" if n != 1 else ""} at runtime</h3>
<p>A build-time scan of <code>{esc(c.product_file)}</code> found these absolute URLs loaded as scripts, stylesheets or
other resources. The product needs a network connection to them, and its page needs a CSP that allows them
(see the play-page notes in <code>site/DEPLOY.md</code>).</p>
<ul class="url-list">{urls}</ul>
{q}
</div>""")
    if c.alert_calls:
        n = c.alert_calls
        patched = []
        for j in site.model.judges:
            letter = _letter(j, c.slug)
            if letter and j.alerts_patched.get(letter):
                patched.append(f"the {esc(j.label)} judge got a copy in which {j.alerts_patched[letter]} "
                               f"<code>alert(</code> call{'s' if j.alerts_patched[letter] != 1 else ''} had been rewritten to "
                               f"<code>console.log(</code>")
        pnote = (f'<p>According to <code>Judge/judge-mapping.json</code> (<code>alerts_patched</code>), {"; ".join(patched)}. '
                 f'{site.evidence("Judge/judge-mapping.json", "judge-mapping.json")}</p>') if patched else ""
        items = _review_lines(site, c, ALERT_RE) + _judge_lines(site, c, ALERT_RE) + _process_lines(site, c, ALERT_RE)
        q = _quote_block(site, items)
        blocks.append(f"""<div class="caveat warn">
<h3>Calls the native <code>alert()</code> dialog</h3>
<p>A build-time scan of <code>{esc(c.product_file)}</code> found {n} <code>alert(</code> call{"s" if n != 1 else ""}.
Native dialogs block the page until dismissed. The copy under <a href="{play_url(c)}">Play</a> is unmodified.</p>
{pnote}
{q}
</div>""")
    return "\n".join(blocks)


def _qr(site: Site, c) -> str:
    url = site.abs_url(f"play/{c.slug}/")
    svg = qr.svg(url, title=f"QR code for {url}")
    # break the URL only after a '/', never inside a slug
    url_html = "/<wbr>".join(esc(part) for part in url.split("/"))
    return f"""<div class="qr-block">
<div class="qr-tile">{svg}</div>
<p class="qr-intro">Scan to open the product on a phone or headset browser. The code encodes the product's absolute URL:</p>
<p class="qr-url"><code>{url_html}</code></p>
<p class="small muted qr-note">WebXR sessions need HTTPS and a browser with WebXR support (for example the Meta Quest
Browser or Chrome on Android). No headset session was entered during the experiment; see the
<a href="@/methodology/#caveats">caveats</a>.</p>
</div>"""


def _glance(site: Site, c) -> str:
    m = site.model
    ranks = m.ranks(c.slug)
    jrows = []
    for j in m.judges:
        rk = ranks.get(j.id)
        cell = (f'<td class="num"><strong>{rk}</strong> <span class="muted">/ {len(j.rows)}</span></td>' if rk
                else '<td class="num muted">–</td>')
        jrows.append(f'<tr><th scope="row"><a href="{judge_url(j)}">{esc(j.label)}</a></th>{cell}</tr>')
    sp = m.spread(c.slug)
    if ranks:
        jrows.append(f'<tr class="derived-row"><th scope="row">Mean rank {DERIVED}</th><td class="num"><strong>{_mean_html(site, c)}</strong></td></tr>')
        jrows.append(f'<tr class="derived-row"><th scope="row">Spread {DERIVED}</th><td class="num">{sp[0]}–{sp[1]} · σ {sp[2]:.2f}</td></tr>')
    srows = []
    vals = []
    for tid, _f, label in m.review_types:
        r = m.review(tid, c.slug)
        if r:
            vals.append(r.overall)
            srows.append(f'<tr><th scope="row"><a href="{review_url(r)}">{esc(label)}</a></th>'
                         f'<td class="num"><strong>{esc(fmt_score(r.overall))}</strong> <span class="muted">/ 10</span></td></tr>')
        else:
            srows.append(f'<tr><th scope="row">{esc(label)}</th><td class="num muted">–</td></tr>')
    if vals:
        srows.append(f'<tr class="derived-row"><th scope="row">Mean score {DERIVED}</th>'
                     f'<td class="num">{sum(vals) / len(vals):.2f}</td></tr>')
        srows.append(f'<tr class="derived-row"><th scope="row">Range {DERIVED}</th>'
                     f'<td class="num">{esc(fmt_score(min(vals)))}–{esc(fmt_score(max(vals)))}</td></tr>')
    return f"""<div class="glance">
<div class="table-wrap"><table class="glance-t">
<caption>Phase 2: rank given by each blind judge (1 = best).</caption>
<thead><tr><th scope="col">Judge</th><th scope="col" class="num">Rank</th></tr></thead>
<tbody>{"".join(jrows)}</tbody></table></div>
<div class="table-wrap"><table class="glance-t">
<caption>Phase 1: overall score of each blind review (1–10).</caption>
<thead><tr><th scope="col">Review</th><th scope="col" class="num">Overall</th></tr></thead>
<tbody>{"".join(srows)}</tbody></table></div>
</div>
<p class="small muted">Derived values: mean rank = {esc(_how_mean(site, c))}; spread = lowest–highest rank and the
population standard deviation σ of those ranks; mean score = arithmetic mean of the phase-1 overall scores;
range = lowest–highest of them. A “–” means no rank or review exists.</p>"""


def _overall_html(site: Site, r) -> str:
    return line_html(site, r.files.get("REVIEW.md", r.dir), r.overall_line)


_BARE_OVERALL = re.compile(r"\s*overall(?: score)?\s*:?\s*([\d.]+)\s*(?:/\s*10)?\s*", re.I)


def _overall_is_bare(r) -> bool:
    """True when the review's overall-score line says nothing beyond the score itself ('**Overall score: 8 / 10**'),
    so the large figure already shows all of it; any other wording (a reason, a rounding note) is quoted."""
    plain = re.sub(r"[#*_`|]", " ", r.overall_line)
    mt = _BARE_OVERALL.fullmatch(plain)
    return bool(mt) and float(mt.group(1)) == r.overall


def _overall_block(site: Site, r, src: str, line: int | None) -> str:
    """The large overall score, sourced to its line in REVIEW.md. The line is quoted verbatim only when it says
    more than the number (otherwise the quote would just repeat the figure next to it)."""
    ev = _ev(site, src, "REVIEW.md" + (f" line {line}" if line else ""), line)
    num = (f'<p class="overall-num"><span class="big">{esc(fmt_score(r.overall))}</span><span class="muted"> / 10</span> '
           f'<span class="muted small">overall</span></p>')
    if _overall_is_bare(r):
        return (f'<div class="overall overall-bare">{num}'
                f'<p class="small muted overall-src">The reviewer’s overall-score line — {ev}</p></div>')
    return (f'<div class="overall">{num}<blockquote class="quote overall-line"><p>{_overall_html(site, r)}</p>'
            f'<cite>Overall-score line, verbatim — {ev}</cite></blockquote></div>')


def _criteria(site: Site, c) -> str:
    m = site.model
    out = []
    for tid, _f, label in m.review_types:
        r = m.review(tid, c.slug)
        if not r:
            continue
        src = r.files.get("REVIEW.md", r.dir)
        rows = "".join(f'<tr><th scope="row">{esc(cr.name)}</th><td class="num"><strong>{esc(fmt_score(cr.score))}</strong></td>'
                       f"<td>{inline(site, src, cr.reason)}</td></tr>" for cr in r.criteria)
        ev = [site.evidence(r.files[n], n) for n in ("REVIEW.md", "PROMPT.txt") if n in r.files]
        if "TRANSCRIPT.md" in r.files:
            ev.append(f'<span class="evidence"><a href="{esc(site.local(r.files["TRANSCRIPT.md"]))}">review agent transcript</a>'
                      f' <a class="gh" href="{esc(site.gh(r.files["TRANSCRIPT.md"]))}" rel="noopener">GitHub</a></span>')
        line = find_line(r.md, r.overall_line)
        out.append(f"""<section class="review-block" aria-labelledby="rv-{esc(tid)}">
<h3 id="rv-{esc(tid)}">{esc(label)} review <span class="muted small">reviewed blind as <code>{esc(r.blind_id)}</code></span></h3>
{_overall_block(site, r, src, line)}
<figure class="chart-fig">{_bar_chart(r, c, True)}{_bar_chart(r, c, False)}<figcaption class="small muted">Criterion scores (0–10 axis). Same data, with the reviewer's reasons, in the table below.</figcaption></figure>
<div class="table-wrap"><table class="crit-table">
<caption>{esc(label)} review criteria with the reviewer's one-line reasons, verbatim.</caption>
<thead><tr><th scope="col">Criterion</th><th scope="col" class="num">Score</th><th scope="col">One-line reason (verbatim)</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="small evidence-row">Evidence: {" · ".join(ev)} · <a href="{review_url(r)}">full review page</a></p>
</section>""")
    if not out:
        return '<p class="muted">No phase-1 review of this candidate exists.</p>'
    ncrit = sorted({len(r.criteria) for r in m.reviews})
    crit = f"{ncrit[0]} criteria" if len(ncrit) == 1 else "criteria"
    return (f"<p>Each review type had its own {crit}, so each is charted separately. Scores are the reviewers' own; "
            "the reasons are quoted verbatim.</p>" + "\n".join(out))


def _judges(site: Site, c) -> str:
    m = site.model
    items, missing = [], []
    for j in m.judges:
        row = next((r for r in j.rows if r.slug == c.slug), None)
        if not row:
            missing.append(f'<a href="{judge_url(j)}">{esc(j.label)}</a>')
            continue
        p = j.files["RANKING.md"]
        line = find_line(j.md, row.justification)
        mat = f' <span class="muted small">· {"hands-on in a browser" if j.browser else "static material"}</span>'
        items.append(f"""<li class="judge-item">
<div class="judge-rank" aria-hidden="true"><span class="big">{row.rank}</span><span class="muted small">/ {len(j.rows)}</span></div>
<div class="judge-body">
<h3><a href="{judge_url(j)}">{esc(j.label)} judge</a>{mat}</h3>
<p class="small muted">Rank <strong>{row.rank}</strong> of {len(j.rows)} · saw this candidate as letter <strong class="letter">{esc(row.letter)}</strong> · judged against prompt {prompt_badge(j.letter_prompt.get(row.letter, row.prompt))}</p>
<blockquote class="quote"><p>{inline(site, p, row.justification)}</p>
<cite>{esc(j.label)} judge, ranking justification for {esc(row.letter)}, verbatim — {_ev(site, p, "RANKING.md" + (f" line {line}" if line else ""), line)}</cite></blockquote>
</div>
</li>""")
    note = (f'<p class="small muted">Not ranked by: {", ".join(missing)}.</p>' if missing else "")
    if not items:
        return '<p class="muted">No judge ranked this candidate.</p>' + note
    return (f'<p>Each judge saw the candidates under its own shuffled letters, without names. The rank and justification '
            f'are quoted from the judge’s <code>RANKING.md</code>.</p><ol class="judge-list">{"".join(items)}</ol>{note}')


def _specials(site: Site, c) -> str:
    m = site.model
    items = []
    for j in m.judges:
        p = j.files["RANKING.md"]
        for s in j.special:
            if c.slug not in s.slugs:
                continue
            letters = []
            for L, sl in zip(s.letters, s.slugs):
                who = "this candidate" if sl == c.slug else _label_link(m.cand(sl))
                letters.append(f'<span class="letter">{esc(L)}</span> = {who}')
            line = find_line(j.md, s.raw)
            items.append(f"""<li><blockquote class="quote"><p>{inline(site, p, s.raw)}</p>
<cite><a href="{judge_url(j)}">{esc(j.label)} judge</a> · {"; ".join(letters)} — {_ev(site, p, "RANKING.md" + (f" line {line}" if line else ""), line)}</cite></blockquote></li>""")
    if not items:
        return ('<p class="muted">No judge listed a special element for this candidate. '
                'See the <a href="@/techniques/">techniques catalog</a> for every element.</p>')
    return (f'<p>Bullets from the judges’ “Special elements” sections that name this candidate, quoted verbatim. '
            f'Letters are the judge’s blind labels. All elements, grouped by technique, are in the '
            f'<a href="@/techniques/">techniques catalog</a>.</p><ul class="special-list">{"".join(items)}</ul>')


def _gallery(site: Site, c) -> str:
    groups: dict[str, list] = {}
    for s in c.shots:
        groups.setdefault(s.source_id, []).append(s)
    if not groups:
        return '<p class="muted">No screenshots were taken of this candidate.</p>'
    m = site.model
    out = []
    for sid, shots in groups.items():
        first = shots[0]
        if first.source == "review":
            tid = sid.split("/", 1)[0]
            r = m.review(tid, c.slug)
            src = r.files.get("REVIEW.md", r.dir) if r else ""
            head = f'<a href="{review_url(r)}">{esc(first.source_label)}</a>' if r else esc(first.source_label)
        else:
            j = m.judge(sid)
            src = j.files["RANKING.md"]
            head = f'<a href="{judge_url(j)}">{esc(first.source_label)}</a>'
        caps = {s.caption for s in shots}
        shared = len(shots) > 1 and len(caps) == 1 and first.caption
        figs = []
        for s in shots:
            f = figure(site, s)
            if s.caption and not shared:
                f = f.replace("</figcaption></figure>",
                              f'<span class="cap-quote">“{line_html(site, src, s.caption)}”</span></figcaption></figure>')
            figs.append(f)
        sharedq = (f'<blockquote class="quote small"><p>{line_html(site, src, first.caption)}</p>'
                   f'<cite>Caption line, verbatim — {site.evidence(src, os.path.basename(src))}</cite></blockquote>') if shared else ""
        out.append(f'<section class="shot-group"><h3>{head} <span class="muted small">{len(shots)} screenshot{"s" if len(shots) != 1 else ""}</span></h3>'
                   f'{sharedq}<div class="gallery">{"".join(figs)}</div></section>')
    return ("<p>Screenshots taken by the browser reviewers and browser judges in desktop Chrome, grouped by who took them. "
            "Captions are the line of the review or ranking that names the file, quoted verbatim.</p>" + "\n".join(out))


def _facts(site: Site, c) -> str:
    m = site.model
    sha_text = _read(site, m.sha_file)
    sha_line = find_line(sha_text, c.html_path)
    readme = "ReviewOrchestrator/README.md"
    bytes_note = ""
    if os.path.isfile(os.path.join(site.repo, readme)):
        rt = _read(site, readme)
        bl = find_line(rt, f"`{c.folder}`")
        if bl and f"({c.bytes:,}" in rt.splitlines()[bl - 1]:
            bytes_note = f' <span class="small muted">matches {_ev(site, readme, "ReviewOrchestrator/README.md §1", bl)}</span>'
    ext = ("none" if not c.external else
           "<ul class=\"plain\">" + "".join(f"<li><code>{esc(u)}</code></li>" for u in c.external) + "</ul>")
    letters = []
    for j in m.judges:
        L = _letter(j, c.slug)
        letters.append(f'<a href="{judge_url(j)}">{esc(j.label)}</a>: ' + (f'<span class="letter">{esc(L)}</span>' if L else "–"))
    blind = []
    for nn in _blind_ids(site, c.slug):
        blind.append(f"<code>{esc(nn)}</code>")
    rows = [
        ("Folder", f'<code>{esc(c.folder)}/</code> <span class="small muted">{site.evidence(c.folder, "files")}</span>'),
        ("Vendor", esc(c.vendor)),
        ("Product", esc(c.product)),
        ("Model (as recorded)", f"<code>{esc(c.model)}</code>"),
        ("Effort (as recorded)", esc(c.effort)),
        ("Provenance", inline(site, "site/candidates.toml", c.provenance)),
        ("Prompt", f'<a class="badge-link" href="@/methodology/#prompts">{prompt_badge(c.prompt)}</a> <code>prompt{esc(c.prompt[1:])}.txt</code>'),
        ("Chat date", esc(c.date)),
        ("Source chat", f'<a href="{esc(c.source_url)}" rel="noopener">{esc(c.source_url)}</a>'),
        ("Product file", f"<code>{esc(c.product_file)}</code>"),
        ("Size", f"{c.bytes:,} bytes{bytes_note}"),
        ("sha256", f'<code class="sha">{esc(c.sha256)}</code><br><span class="small muted">matches '
                   f'<code>{esc(m.sha_file)}</code> (checked at build time) · '
                   f'{_ev(site, m.sha_file, "source-html.sha256" + (f" line {sha_line}" if sha_line else ""), sha_line)}</span>'),
        ("External dependencies", ext + ' <span class="small muted">(build-time scan)</span>'),
        ("<code>alert(</code> calls", f"{c.alert_calls} <span class=\"small muted\">(build-time scan)</span>"),
        ("Phase-1 blind id", ", ".join(blind) or "–"),
        ("Judge letters", " · ".join(letters) or "–"),
    ]
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    return (f'<dl class="facts">{dl}</dl><p class="small muted">Model, effort and provenance are as recorded in '
            f'{site.evidence("site/candidates.toml", "site/candidates.toml")}; size, sha256, external resources and '
            f'<code>alert(</code> calls are computed from the product file at build time.</p>')


def _links(site: Site, c) -> str:
    m = site.model
    li = [f'<li><a href="{esc(site.local(c.transcription))}">Chat transcript</a> <span class="muted small">(the original chat, <code>TRANSCRIPTION.md</code>)</span> '
          f'<a class="gh small" href="{esc(site.gh(c.transcription))}" rel="noopener">GitHub</a></li>']
    for tid, _f, label in m.review_types:
        r = m.review(tid, c.slug)
        if not r:
            continue
        t = (f' · <a href="{esc(site.local(r.files["TRANSCRIPT.md"]))}">agent transcript</a>' if "TRANSCRIPT.md" in r.files else "")
        li.append(f'<li><a href="{review_url(r)}">{esc(label)} review</a>{t}</li>')
    li.append(f'<li><a href="{esc(site.gh(c.html_path))}" rel="noopener">Product source on GitHub</a> · <a href="{play_url(c)}">Play</a></li>')
    others = [o for o in m.ordered() if o.slug != c.slug]
    cmp = "".join(f'<li><a href="{compare_url(c, o)}">vs {esc(o.label)}</a></li>' for o in others)
    return (f'<ul class="link-list">{"".join(li)}</ul>'
            + (f'<h3>Compare side by side</h3><ul class="compare-list">{cmp}</ul>' if others else ""))


# ---------------------------------------------------------------- candidate page

def build_candidate(site: Site, c) -> None:
    m = site.model
    sections: list[tuple[str, str, str]] = []
    warn = _warnings(site, c)
    if warn:
        sections.append(("warnings", "Warnings", warn))
    sections += [
        ("device", "Open on a device", _qr(site, c)),
        ("glance", "Results at a glance", _glance(site, c)),
        ("criteria", "Phase-1 criteria", _criteria(site, c)),
        ("judges", "Judges", _judges(site, c)),
        ("special", "Special elements noted", _specials(site, c)),
        ("screenshots", "Screenshots", _gallery(site, c)),
        ("facts", "Facts", _facts(site, c)),
        ("links", "Links", _links(site, c)),
    ]
    toc = "".join(f'<li><a href="#{sid}">{esc(t)}</a></li>' for sid, t, _ in sections)
    secs = "\n".join(f'<section id="{sid}" class="cand-sec" aria-labelledby="{sid}-h"><h2 id="{sid}-h">{esc(t)}</h2>\n{html}\n</section>'
                     for sid, t, html in sections)
    body = f"""{_header(site, c)}
<div class="cand-layout">
<nav class="cand-toc" aria-label="On this page"><p class="cand-toc-h">On this page</p><ol>{toc}</ol></nav>
<div class="cand-content">
{secs}
</div>
</div>"""
    site.page(f"candidates/{c.slug}/index.html", c.label, body, section="candidates",
              crumbs=[("Candidates", "candidates/"), (c.label, f"candidates/{c.slug}/")],
              description=f"{c.label} ({c.vendor} · {c.product}, prompt {c.prompt}): play it, its phase-1 reviews, "
                          f"every judge's verbatim justification, screenshots and facts.")
    facts = [c.label, c.name, c.vendor, c.product, c.model, c.effort, md.to_text(c.provenance), f"prompt {c.prompt}",
             c.product_file, f"{c.bytes} bytes", c.sha256, c.folder, " ".join(_blind_ids(site, c.slug)),
             " ".join(c.external), f"alert calls {c.alert_calls}" if c.alert_calls else ""]
    site.search_doc(f"candidates/{c.slug}/", c.label, "page", f"Candidate · {c.vendor} · {c.product}",
                    " ".join(x for x in facts if x))


def build(site: Site) -> None:
    build_index(site)
    for c in site.model.candidates:
        build_candidate(site, c)
