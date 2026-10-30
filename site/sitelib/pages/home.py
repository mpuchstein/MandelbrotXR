"""Home page (index.html): explainer, headline result (quoted + derived check), caveats,
overview cards for every candidate, a compact ranking and quick links.

Everything is computed from the model; the only quoted prose is the "The judges broadly agree"
passage of Judge/README.md, rendered verbatim.
"""
from __future__ import annotations

import re
from fractions import Fraction

from .. import img, md
from ..data import DataError
from ..fragments import caveats_html, cand_url, fmt_mean, judge_url, marker_svg, render_md, standing_html
from ..layout import Site, esc
from . import candidates as _candidates

ORDER = 100

README = "Judge/README.md"
PASSAGE_START = "The judges broadly agree"
# Hero: one build-time render (about 5 s), shown as a framed picture beside the title on a neutral surface.
HERO_W, HERO_H = 720, 240
HERO_VIEW = dict(center=(-0.7436, 0.1318), span=0.03, max_iter=250)

_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]


def words(n: int, cap: bool = False) -> str:
    """Small counts as words ('eight'), larger ones as digits."""
    w = _WORDS[n] if 0 <= n < len(_WORDS) else str(n)
    return w[:1].upper() + w[1:] if cap else w


def _count_word(s: str, path: str) -> int:
    s = s.strip().lower()
    if s.isdigit():
        return int(s)
    if s in _WORDS:
        return _WORDS.index(s)
    raise DataError(f"{path}: cannot read the count {s!r} in the '{PASSAGE_START}' passage")


def _and(items: list[str]) -> str:
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


# ---------------------------------------------------------------- headline passage

def headline_passage(site: Site) -> tuple[str, int]:
    """(Markdown text, 1-based line number) of the 'The judges broadly agree' paragraph and the
    list that follows it, up to the next '## ' heading. Fails loudly if it is missing."""
    with open(f"{site.repo}/{README}", encoding="utf-8") as f:
        lines = f.read().split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith(PASSAGE_START)), None)
    if start is None:
        raise DataError(f"{README}: no line starting with {PASSAGE_START!r} (the home page quotes it)")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    text = "\n".join(lines[start:end]).strip("\n")
    if "\n" not in text:
        raise DataError(f"{README}: the {PASSAGE_START!r} passage has no list after it")
    return text, start + 1


# ---------------------------------------------------------------- derived checks

def _top_bottom_k(text: str) -> tuple[int, int]:
    top = re.search(r"\*\*Top (\w+):\*\*", text)
    bot = re.search(r"\*\*Bottom (\w+):\*\*", text)
    if not top or not bot:
        raise DataError(f"{README}: the {PASSAGE_START!r} passage lacks a '**Top N:**' or '**Bottom N:**' bullet")
    return _count_word(top.group(1), README), _count_word(bot.group(1), README)


def _names(site: Site, slugs) -> str:
    m = site.model
    return _and([f'<a href="{cand_url(m.cand(s))}">{esc(m.cand(s).label)}</a>' for s in slugs])


def _ties_note(site: Site, slugs: list[str]) -> str:
    m = site.model
    groups: dict[Fraction, list[str]] = {}
    for s in slugs:
        groups.setdefault(m.mean_rank(s), []).append(s)
    notes = [f"{_and([esc(m.cand(s).label) for s in g])} tie on mean rank {fmt_mean(mean)}"
             for mean, g in groups.items() if len(g) > 1]
    return (" " + "; ".join(notes) + ".") if notes else ""


def derived_check(site: Site, k_top: int, k_bot: int) -> str:
    m = site.model
    ranked = [c.slug for c in m.ordered() if m.mean_rank(c.slug) is not None]
    judges = m.judges
    nj = len(judges)
    out = []

    def block(label: str, k: int, sel: list[str], judge_set) -> str:
        agree = [j for j in judges if judge_set(j, k) == set(sel)]
        differ = [j for j in judges if j not in agree]
        st = m.standing()
        boundary = ""
        if len(ranked) > k:
            inside, outside = ranked[k - 1] if k else None, ranked[k]
            if inside and m.mean_rank(inside) == m.mean_rank(outside):
                boundary = f" {esc(m.cand(outside).label)} ties with the last of them on mean rank {fmt_mean(m.mean_rank(outside))}."
        diff = ""
        if differ:
            diff = " Differs: " + ", ".join(f'<a href="{judge_url(j)}">{esc(j.label)}</a>' for j in differ) + "."
        these = f"these {words(k)}" if k != 1 else "this candidate"
        return (f'<div class="home-check-row"><h4>{esc(label)} by mean rank</h4>'
                f"<p>{_names(site, sel)}.{_ties_note(site, sel)}{boundary}</p>"
                f'<p class="home-check-agree"><span class="home-frac">{len(agree)}/{nj}</span> '
                f"judges have {these} in their {esc(label.lower())}.{diff}</p></div>")

    top = ranked[:k_top]
    bot = ranked[-k_bot:] if k_bot else []
    out.append(block(f"Top {k_top}", k_top, top, lambda j, k: {r.slug for r in j.rows if r.rank <= k}))
    out.append(block(f"Bottom {k_bot}", k_bot, bot, lambda j, k: {r.slug for r in j.rows if r.rank > len(j.rows) - k}))

    # each judge's largest deviation from the consensus (mean rank over all judges)
    rows = []
    order = {c.slug: i for i, c in enumerate(m.ordered())}
    for ji, j in enumerate(judges):
        best = None
        for r in j.rows:
            mean = m.mean_rank(r.slug)
            d = Fraction(r.rank) - mean
            key = (-abs(d), order[r.slug])
            if best is None or key < best[0]:
                best = (key, r, mean, d)
        if best:
            rows.append((best[0][0], ji, j, best[1], best[2], best[3]))
    rows.sort(key=lambda t: (t[0], t[1]))
    trs = []
    for _, _, j, r, mean, d in rows:
        c = m.cand(r.slug)
        sign = "+" if d > 0 else ("−" if d < 0 else "±")
        trs.append(f'<tr><th scope="row"><a href="{judge_url(j)}">{esc(j.label)}</a></th>'
                   f'<td><a href="{cand_url(c)}">{esc(c.label)}</a></td>'
                   f'<td class="num">{r.rank}</td><td class="num">{fmt_mean(mean)}</td>'
                   f'<td class="num"><span class="home-delta">{sign}{abs(float(d)):.1f}</span></td></tr>')
    dev = (f'<div class="home-check-row"><h4>Largest deviation from consensus, per judge</h4>'
           f'<div class="table-wrap"><table class="home-dev"><thead><tr><th scope="col">Judge</th><th scope="col">Candidate</th>'
           f'<th scope="col" class="num">Rank</th><th scope="col" class="num">Mean</th><th scope="col" class="num">Δ</th></tr></thead>'
           f'<tbody>{"".join(trs)}</tbody></table></div>'
           f'<p class="small muted">Rank = that judge’s rank; Δ = rank − mean rank; + means the judge placed it lower (worse) '
           f'than the consensus. For each judge the candidate with the largest |Δ| is shown, largest first.</p></div>')
    out.append(dev)
    return ('<section class="card home-check" aria-labelledby="home-check-h">'
            '<h3 id="home-check-h">Checked against the data <span class="derived">derived</span></h3>'
            f'<p class="small muted">Computed by this site from the {words(nj)} <code>RANKING.md</code> files and '
            '<code>judge-mapping.json</code>. Mean rank = the average of a candidate’s ranks over the judges that ranked it; '
            'candidates with equal means share a place.</p>'
            + "".join(out) + "</section>")


# ---------------------------------------------------------------- pieces

def hero(site: Site) -> str:
    m = site.model
    png = img.mandelbrot_png(HERO_W, HERO_H, dark=True, **HERO_VIEW)
    site.write("media/hero.png", png)
    nc, nj = len(m.candidates), len(m.judges)
    sub = (f"{words(nc, True)} AI coding assistants each built a WebXR Mandelbrot room; "
           f"blind reviewers scored every build and {words(nj)} blind judges ranked them.")
    stats = [(nc, "candidates"), (len({c.prompt for c in m.candidates}), "prompts"),
             (len(m.reviews), "blind reviews"), (nj, "blind judges")]
    dl = "".join(f'<div><dt>{esc(label)}</dt><dd>{n}</dd></div>' for n, label in stats)
    return (f'<section class="home-hero" aria-labelledby="home-title">'
            f'<div class="home-hero-text"><p class="home-kicker">Experiment results</p>'
            f'<h1 id="home-title">MandelbrotXR</h1><p class="home-sub">{esc(sub)}</p>'
            f'<dl class="home-stats">{dl}</dl></div>'
            f'<img class="home-hero-img" src="@/media/hero.png" width="{HERO_W}" height="{HERO_H}" alt="" decoding="async" fetchpriority="high">'
            f'</section>')


def explainer(site: Site) -> tuple[str, str]:
    """(HTML paragraph, plain text for search)."""
    m = site.model
    nc = len(m.candidates)
    prompts = sorted({c.prompt for c in m.candidates})
    per = [f"{p} for {words(sum(1 for c in m.candidates if c.prompt == p))}" for p in prompts]
    pl = _and([f'<a href="@/methodology/#prompts">{esc(p)}</a>' for p in prompts])
    ncrit = sorted({len(r.criteria) for r in m.reviews})
    crit = f"{words(ncrit[0])} criteria" if len(ncrit) == 1 else "a set of criteria"
    types = [label for _, _, label in m.review_types]
    jlinks = _and([f'<a href="{judge_url(j)}">{esc(j.label)}</a>' for j in m.judges])
    all_ranked = all(len(j.rows) == nc for j in m.judges)
    ranked = f"ranked all {words(nc)} from best to worst" if all_ranked else "ranked the candidates they were given from best to worst"
    html = (f'<p class="lede home-lede">{words(nc, True)} AI coding assistants each built a standalone WebXR page that '
            f'visualizes the Mandelbrot set in a virtual room, from one of {words(len(prompts))} prompts ({pl}; '
            f'{", ".join(esc(x) for x in per)} builds). '
            f'In phase 1, every page was reviewed blind by {words(len(types))} kinds of reviewer '
            f'(<a href="@/judges/">{esc(_and(types))}</a>), each scoring {crit} from 1 to 10 plus an overall score. '
            f'In phase 2, {words(len(m.judges))} blind judges, each working from different material ({jlinks}), '
            f'{ranked}. The mean of those ranks is the consensus used below.</p>')
    text = re.sub(r"<[^>]+>", "", html)
    return html, text


def headline(site: Site) -> tuple[str, str]:
    text, line = headline_passage(site)
    k_top, k_bot = _top_bottom_k(text)
    quote = render_md(site, README, text=text, heading_ids=False)
    cite = site.evidence(README, README, anchor=f"#L{line}", line=line)
    html = (f'<section class="home-headline" aria-labelledby="home-headline-h">'
            f'<h2 id="home-headline-h">Headline result</h2>'
            f'<div class="home-headline-grid">'
            f'<figure class="quote home-quote"><blockquote>{quote}</blockquote>'
            f'<figcaption class="cite">Quoted verbatim from {cite}, below the aggregated rank table.</figcaption></figure>'
            f'{derived_check(site, k_top, k_bot)}{caveats_html(compact=True)}</div></section>')
    return html, md.to_text(text)


def card(site: Site, c) -> str:
    """The candidate card, identical to the one on candidates/ (same component, wording and score
    display: series swatch, prompt badge, mean rank + standing, score chips), one heading level down
    because on the home page the cards sit under the "All N candidates" h2."""
    html = _candidates._card(site, c)
    html = re.sub(r"<h2( class=\"cand-title\".*?)</h2>", r"<h3\1</h3>", html, count=1, flags=re.S)
    return f"<li>{html}</li>"


def _strip(m, c, n: int) -> str:
    """Tiny dot strip of one candidate's ranks on a 1..n scale, in the candidate's series colour.
    The same numbers are printed in the row, which is its table equivalent."""
    w, h, pad = 132, 24, 7
    x = lambda r: pad + (w - 2 * pad) * (float(r) - 1) / max(1, n - 1)
    seen: dict[int, int] = {}
    dots, said = [], []
    for j in m.judges:
        r = j.rank.get(c.slug)
        if r is None:
            continue
        k = seen.get(r, 0)
        seen[r] = k + 1
        y = h / 2 + (0 if k == 0 else (-1) ** k * 3.0 * ((k + 1) // 2))
        dots.append(marker_svg(c.index, x(r), y, r=3.2))
        said.append(f"{j.label} {r}")
    mean = m.mean_rank(c.slug)
    mk = f'<line class="home-strip-mean" x1="{x(mean):.1f}" x2="{x(mean):.1f}" y1="2" y2="{h - 2}"/>' if mean is not None else ""
    desc = f"Ranks on a 1 to {n} scale: {', '.join(said) or 'none'}; mean {fmt_mean(mean)}."
    return (f'<svg class="home-strip" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" focusable="false">'
            f'<title>Rank strip for {esc(c.label)}</title><desc>{esc(desc)}</desc>'
            f'<line class="home-strip-axis" x1="{pad}" x2="{w - pad}" y1="{h / 2:.1f}" y2="{h / 2:.1f}"/>'
            f'{mk}<g class="home-strip-dots">{"".join(dots)}</g></svg>')


def compact_ranking(site: Site) -> str:
    m = site.model
    n = len(m.candidates)
    heads = "".join(f'<th scope="col" class="num"><a href="{judge_url(j)}">{esc(j.label)}</a></th>' for j in m.judges)
    rows = []
    for c in m.ordered():
        r = m.ranks(c.slug)
        cells = "".join(f'<td class="num">{r[j.id] if j.id in r else "–"}</td>' for j in m.judges)
        rows.append(f'<tr><th scope="row"><a href="{cand_url(c)}">{esc(c.label)}</a></th>'
                    f'<td class="num home-pl">{standing_html(m, c)}</td>'
                    f'<td class="num home-meancell">{fmt_mean(m.mean_rank(c.slug))}</td>{cells}'
                    f'<td class="home-stripcell">{_strip(m, c, n)}</td></tr>')
    return (f'<section class="home-ranking" aria-labelledby="home-ranking-h">'
            f'<h2 id="home-ranking-h">Compact ranking</h2>'
            f'<p class="muted">Each judge’s rank (1 = best) and the mean <span class="derived">derived</span>. '
            f'The strip plots the {words(len(m.judges))} ranks on a 1–{n} scale; the vertical tick is the mean. '
            f'The <a href="@/rankings/">rankings page</a> has the full sortable matrix, spread and judge agreement.</p>'
            f'<div class="table-wrap matrix-wrap"><table class="home-rank-table">'
            f'<caption>Phase-2 ranks by judge, ordered by mean rank.</caption>'
            f'<thead><tr><th scope="col">Candidate</th><th scope="col" class="num">Standing</th>'
            f'<th scope="col" class="num">Mean</th>{heads}<th scope="col"><span class="sr-only">Rank strip</span></th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="small muted">Same numbers as the aggregated table in {site.evidence(README, README)}.</p>'
            f'<p><a class="btn" href="@/rankings/">Open the full rankings</a></p></section>')


QUICK = [
    ("rankings/", "Rankings", "Sortable judge × candidate matrix with spread, Kendall τ agreement and a bump chart."),
    ("compare/", "Compare", "Any two candidates side by side: scores, ranks, justifications, screenshots."),
    ("techniques/", "Techniques", "Every special element the judges credited, grouped by technique, plus claim-vs-code mismatches."),
    ("judges/", "Judges & reviews", "Each judge’s material, prompt, criteria and ranking, with a blind/reveal toggle; every phase-1 review."),
    ("methodology/", "Methodology", "Pipeline, blinding, incidents, environment limits and both prompts verbatim."),
    ("data/", "Data", "results.json and CSVs with a documented schema, plus the changelog and Atom feed."),
]


def quick_links() -> str:
    items = "".join(f'<li><a class="card home-ql" href="@/{p}"><span class="home-ql-t">{esc(t)}</span>'
                    f'<span class="home-ql-d">{esc(d)}</span></a></li>' for p, t, d in QUICK)
    form = ('<form class="home-search card" action="@/search/" method="get" role="search">'
            '<label for="home-q" class="home-ql-t">Search</label>'
            '<span class="home-ql-d">Full text over reviews, rankings, judge summaries and transcripts.</span>'
            '<span class="home-search-row"><input id="home-q" name="q" type="search" placeholder="e.g. perturbation" autocomplete="off">'
            '<button class="btn btn-primary" type="submit">Search</button></span></form>')
    return (f'<section class="home-quick" aria-labelledby="home-quick-h"><h2 id="home-quick-h">Explore</h2>'
            f'<ul class="home-ql-grid">{items}<li>{form}</li></ul></section>')


# ---------------------------------------------------------------- page

def build(site: Site) -> None:
    m = site.model
    intro_html, intro_text = explainer(site)
    head_html, head_text = headline(site)
    cards = "".join(card(site, c) for c in m.ordered())
    body = (hero(site)
            + intro_html
            + head_html
            + f'<section class="home-cands" aria-labelledby="home-cands-h"><h2 id="home-cands-h">All {len(m.candidates)} candidates</h2>'
              f'<p class="muted">Ordered by mean rank; the same cards as on the <a href="@/candidates/">Candidates</a> page. '
              f'Scores are the phase-1 reviewers’ overall scores out of 10; Details has each review and every judge’s '
              f'justification. Play opens the product, unmodified, as a full page.</p>'
              f'<ul class="grid cand-grid home-grid">{cards}</ul></section>'
            + compact_ranking(site)
            + quick_links())
    site.page("index.html", "MandelbrotXR results", body, section="home",
              description=re.sub(r"\s+", " ", intro_text).strip()[:300])
    names = " ".join(c.name for c in m.ordered())
    site.search_doc("index.html", "MandelbrotXR results — home", "page", "Home",
                    re.sub(r"\s+", " ", f"{intro_text} {head_text} {names}").strip())
