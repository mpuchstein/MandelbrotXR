"""Judges & reviews: judges/ (index), judges/<id>/ (one per phase-2 judge), reviews/ (index) and
reviews/<type>/<slug>/ (one per phase-1 review).

Every judge page has a Blind/Reveal toggle (assets/js/reveal.js): both the letter the judge saw and the
revealed candidate are rendered server-side, and the toggle only switches a class on the .reveal-scope
container. Without JavaScript the blind view stays visible and a server-rendered "Revealed mapping"
table (from Judge/judge-mapping.json) sits directly below the ranking, so nothing is lost.
Review pages show the phase-1 candidate-NN blinding the same way (ReviewOrchestrator/blind-mapping.json).

Everything is discovered from the model: judges, review types, letters and candidates are never hardcoded.
"""
from __future__ import annotations

import os
import re

from .. import md
from ..data import Judge, Review, section
from ..fragments import cand_url, fmt_score, judge_url, review_url, render_md, score_heat
from ..layout import Site, cand_link, esc, figure, prompt_badge

ORDER = 600

JUDGE_README = "Judge/README.md"
JUDGE_MAPPING = "Judge/judge-mapping.json"
ORCH_README = "ReviewOrchestrator/README.md"
BLIND_MAPPING = "ReviewOrchestrator/blind-mapping.json"

SCRIPTS = ["reveal.js"]


# ---------------------------------------------------------------- small helpers

def _rel(url: str) -> str:
    """'@/judges/html/' -> 'judges/html/index.html'."""
    return url.removeprefix("@/") + "index.html"


def _read_lines(site: Site, path: str) -> list[str]:
    p = os.path.join(site.repo, path)
    if not os.path.isfile(p):
        return []
    with open(p, encoding="utf-8") as f:
        return f.read().splitlines()


def _find_line(site: Site, path: str, *needles: str) -> tuple[int, str] | None:
    """(1-based line number, line) of the first line containing every needle, or None."""
    for i, line in enumerate(_read_lines(site, path), 1):
        if all(n in line for n in needles):
            return i, line
    return None


def _strip_marker(line: str) -> str:
    return re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line).strip()


def _quote(site: Site, path: str, hit: tuple[int, str] | None, label: str | None = None) -> str:
    """A verbatim one-line quote (inline Markdown rendered) with a line-anchored evidence link."""
    if not hit:
        return ""
    n, line = hit
    from ..fragments import md_link
    body = md.render_inline(_strip_marker(line), link=md_link(site, path))
    cite = site.evidence(path, f"{label or path}, line {n}", anchor=f"#L{n}", line=n)
    return f'<blockquote class="quote"><p>{body}</p><cite>{cite}</cite></blockquote>'


def _line_no(text: str, needle: str) -> int | None:
    for i, line in enumerate(text.splitlines(), 1):
        if line.strip() == needle.strip():
            return i
    return None


def _letters_text(letters) -> str:
    """'A–H' for a contiguous run of single letters, else a comma list."""
    ls = sorted(letters)
    if len(ls) > 2 and all(len(x) == 1 for x in ls) and [ord(x) for x in ls] == list(range(ord(ls[0]), ord(ls[0]) + len(ls))):
        return f"{ls[0]}–{ls[-1]}"
    return ", ".join(ls)


def _md_cell(text: str, src: str, site: Site) -> str:
    from ..fragments import md_link
    return md.render_inline(text, link=md_link(site, src))


def _rv(blind_html: str, reveal_html: str) -> str:
    """Both views, rendered server-side; CSS shows one depending on .is-revealed on the scope."""
    return f'<span class="blind-label">{blind_html}</span><span class="reveal-label">{reveal_html}</span>'


def _toggle(scope_id: str, what_off: str, what_on: str) -> str:
    """The Blind/Reveal button (hidden until reveal.js runs) and its polite status line."""
    return (f'<div class="reveal-bar" role="group" aria-label="Blind or revealed view">'
            f'<button type="button" class="btn reveal-btn" data-reveal-toggle aria-pressed="false" aria-controls="{scope_id}" '
            f'data-label-off="Reveal names" data-label-on="Names revealed" hidden>'
            f'<span class="reveal-icon" aria-hidden="true"></span><span class="reveal-text">Reveal names</span></button>'
            f'<p class="reveal-status small" data-reveal-status data-off="{esc(what_off)}" data-on="{esc(what_on)}" aria-live="polite">{esc(what_off)}</p>'
            f'</div>')


def _toc(items: list[tuple[str, str]]) -> str:
    links = "".join(f'<li><a href="#{esc(i)}">{esc(t)}</a></li>' for i, t in items)
    return f'<nav class="jr-toc" aria-label="On this page"><ul>{links}</ul></nav>'


def _transcript_link(site: Site, files: dict, label: str = "Agent log") -> str:
    p = files.get("TRANSCRIPT.md")
    return site.evidence(p, label) if p else '<span class="muted">—</span>'


def _mode(j: Judge) -> str:
    if j.browser:
        return '<span class="jr-tag jr-tag-browser" title="Tested the products hands-on in a browser">browser</span>'
    return '<span class="jr-tag jr-tag-static" title="Read static material only, never ran the products">static</span>'


# ---------------------------------------------------------------- phase-1 review matrix

def _review_matrix(site: Site, *, caption: str) -> str:
    m = site.model
    types = m.review_types
    head = "".join(f'<th scope="col" class="num">{esc(label)}</th>' for _, _, label in types)
    unblind = {s: nn for nn, s in m.blind.items()}
    rows = []
    for c in m.ordered():
        cells = []
        for tid, _, label in types:
            r = m.review(tid, c.slug)
            if r is None:
                cells.append('<td class="num muted">–</td>')
                continue
            cells.append(f'<td class="num jr-score" style="{score_heat(r.overall)}"><a href="{review_url(r)}">'
                         f'<span class="sr-only">{esc(label)} review of {esc(c.name)}: </span>{esc(fmt_score(r.overall))}</a></td>')
        if not any(m.review(tid, c.slug) for tid, _, _ in types):
            continue
        nn = unblind.get(c.slug, "")
        rows.append(f'<tr><th scope="row">{cand_link(c)} {prompt_badge(c.prompt)}</th>'
                    f'<td><code>{esc(nn) or "–"}</code></td>{"".join(cells)}</tr>')
    return (f'<div class="table-wrap"><table class="jr-matrix"><caption>{caption}</caption>'
            f'<thead><tr><th scope="col">Candidate</th><th scope="col">Blind id</th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def _matrix_caption(site: Site) -> str:
    sec = _find_line(site, ORCH_README, "## 4. Results")
    src = site.evidence(ORCH_README, "ReviewOrchestrator/README.md §4", anchor=f"#L{sec[0]}" if sec else "",
                        line=sec[0] if sec else None)
    return (f"Overall score (1–10) per phase-1 review, parsed from each REVIEW.md (first number of its overall-score line). "
            f"Rows in mean-rank order from phase 2. Each score links to its review page. Ground truth: {src}.")


# ---------------------------------------------------------------- blinding explanations

def _phases_html(site: Site) -> str:
    m = site.model
    n_c, n_t, n_j = len(m.candidates), len(m.review_types), len(m.judges)
    types = ", ".join(label for _, _, label in m.review_types)
    letters = sorted({l for j in m.judges for l in j.mapping})
    p1 = _quote(site, ORCH_README, _find_line(site, ORCH_README, "blind-mapping.json", "shuffled")
                or _find_line(site, ORCH_README, "blind-mapping.json"), "ReviewOrchestrator/README.md")
    p1b = _quote(site, ORCH_README, _find_line(site, ORCH_README, "**Prompts**"), "ReviewOrchestrator/README.md")
    p2a = _quote(site, JUDGE_README, _find_line(site, JUDGE_README, "phase 2"), "Judge/README.md")
    p2 = _quote(site, JUDGE_README, _find_line(site, JUDGE_README, "seeded shuffle"), "Judge/README.md")
    return f"""
<section aria-labelledby="phases" class="jr-phases">
<h2 id="phases">Two phases, two blinding schemes</h2>
<div class="jr-two">
<div class="card">
<h3>Phase 1 · reviews</h3>
<p>{n_t} review types ({esc(types)}) × {n_c} candidates. Each reviewer saw <em>one</em> candidate, under a blind id
<code>candidate-NN</code>, and scored it alone against a shared rubric, ending with an overall score.</p>
<p><strong>Blinding:</strong> one seeded shuffle of the candidate folders onto <code>candidate-NN</code> ids, shared by all
review types. The mapping is {site.evidence(BLIND_MAPPING, "ReviewOrchestrator/blind-mapping.json")}.</p>
{p1}{p1b}
</div>
<div class="card">
<h3>Phase 2 · judges</h3>
<p>{n_j} judges, each with different material, saw all candidates side by side under letters
({esc(_letters_text(letters))}) and produced one comparative ranking.</p>
<p><strong>Blinding:</strong> a separate seeded shuffle per judge onto letters, so the same letter means a different
candidate for each judge. The mapping is {site.evidence(JUDGE_MAPPING, "Judge/judge-mapping.json")}; each judge
folder also has a <code>MAPPING.md</code> written after the judge finished.</p>
{p2a}{p2}
</div>
</div>
<p class="small muted">On every judge page and review page, the <strong>Reveal names</strong> button switches between the label the
agent saw and the candidate behind it; the revealed state is kept in the URL (<code>#reveal</code>) so it can be linked.</p>
</section>"""


# ---------------------------------------------------------------- judges index

def build_judges_index(site: Site) -> None:
    m = site.model
    rows = []
    for j in m.judges:
        first = j.rows[0] if j.rows else None
        last = j.rows[-1] if j.rows else None
        pick = lambda r: (f'{cand_link(m.cand(r.slug))} <span class="muted small">(saw {esc(r.letter)})</span>' if r else "–")
        material = _md_cell(j.material, JUDGE_README, site) if j.material else "—"
        focus = _md_cell(j.focus, JUDGE_README, site) if j.focus else "—"
        rows.append(f'<tr><th scope="row"><a href="{judge_url(j)}">{esc(j.label)}</a></th><td>{material}</td><td>{focus}</td>'
                    f'<td>{_mode(j)}</td><td>{pick(first)}</td><td>{pick(last)}</td><td>{_transcript_link(site, j.files)}</td></tr>')
    jt = _find_line(site, JUDGE_README, "## Judges")
    judges_src = site.evidence(JUDGE_README, "Judge/README.md “Judges” table", anchor=f"#L{jt[0]}" if jt else "",
                               line=jt[0] if jt else None)
    n_rev = len(m.reviews)
    body = f"""
<header class="jr-head">
<p class="jr-eyebrow">Phase 1 and phase 2</p>
<h1>Judges &amp; reviews</h1>
<p class="lede">{len(m.reviews)} blind reviews scored one candidate at a time; then {len(m.judges)} blind judges ranked all
candidates against each other. Every page below shows the material verbatim, with links to the files and agent logs it came from.</p>
</header>
{_toc([("judges", "Judges (phase 2)"), ("reviews", "Reviews (phase 1)"), ("phases", "How the blinding worked")])}
<section aria-labelledby="judges">
<h2 id="judges">Judges <span class="muted jr-count">phase 2 · {len(m.judges)}</span></h2>
<div class="table-wrap"><table class="jr-judges">
<caption>Material and focus verbatim from the {judges_src}. #1 and last pick are revealed via
{site.evidence(JUDGE_MAPPING, "Judge/judge-mapping.json")}; “saw” is the letter the judge used.</caption>
<thead><tr><th scope="col">Judge</th><th scope="col">Material</th><th scope="col">Special-elements focus</th>
<th scope="col">Mode</th><th scope="col">#1 pick</th><th scope="col">Last pick</th><th scope="col">Transcript</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
</section>
<section aria-labelledby="reviews">
<h2 id="reviews">Reviews <span class="muted jr-count">phase 1 · {n_rev}</span></h2>
<p>Each cell is one review; open it for the full verbatim REVIEW.md, its prompt and screenshots.
The <a href="@/reviews/">review list</a> also shows the blind id each reviewer saw and the exact score line.</p>
{_review_matrix(site, caption=_matrix_caption(site))}
</section>
{_phases_html(site)}
"""
    site.page("judges/index.html", "Judges & reviews", body, section="judges", crumbs=[("Judges & reviews", "")],
              description="The phase-2 judges and phase-1 reviews of the MandelbrotXR experiment, with their blinding.")


# ---------------------------------------------------------------- reviews index

def build_reviews_index(site: Site) -> None:
    m = site.model
    parts = []
    for tid, tfolder, label in m.review_types:
        rs = [r for r in m.reviews if r.type_id == tid]
        rs.sort(key=lambda r: r.blind_id or r.slug)
        rows = []
        for r in rs:
            c = m.cand(r.slug)
            n = _line_no(r.md, r.overall_line)
            ev = site.evidence(r.files["REVIEW.md"], "REVIEW.md", anchor=f"#L{n}" if n else "", line=n)
            rows.append(f'<tr><th scope="row"><a href="{review_url(r)}">{esc(r.title)}</a></th>'
                        f'<td>{cand_link(c)} {prompt_badge(c.prompt)}</td>'
                        f'<td class="num">{esc(fmt_score(r.overall))}</td>'
                        f'<td><code class="jr-line">{esc(r.overall_line)}</code> {ev}</td></tr>')
        parts.append(f"""
<section aria-labelledby="t-{esc(tid)}">
<h3 id="t-{esc(tid)}">{esc(label)} reviews <span class="muted jr-count">{len(rs)} · {site.evidence(f"Review/{tfolder}", f"Review/{tfolder}/")}</span></h3>
<div class="table-wrap"><table class="jr-list">
<caption>Sorted by the blind id the reviewer saw. Score = first number of the verbatim line on the right.</caption>
<thead><tr><th scope="col">Review (heading as written)</th><th scope="col">Candidate (revealed)</th>
<th scope="col" class="num">Overall</th><th scope="col">Source line</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
</section>""")
    body = f"""
<header class="jr-head">
<p class="jr-eyebrow">Phase 1</p>
<h1>Reviews</h1>
<p class="lede">{len(m.reviews)} blind reviews: {len(m.review_types)} review types × the candidates. Each reviewer saw one
candidate under a <code>candidate-NN</code> id and scored it alone. See <a href="@/judges/#phases">how the blinding worked</a>.</p>
</header>
<h2 id="matrix">Overall scores</h2>
{_review_matrix(site, caption=_matrix_caption(site))}
<h2 id="all">All reviews by type</h2>
{"".join(parts)}
"""
    site.page("reviews/index.html", "Reviews", body, section="judges",
              crumbs=[("Judges & reviews", "judges/"), ("Reviews", "")],
              description="Every phase-1 review of the MandelbrotXR candidates, with overall scores and blind ids.")


# ---------------------------------------------------------------- one judge

def _alert_quotes(site: Site, j: Judge) -> str:
    """Native-dialog patching: the alerts_patched counts from the mapping plus the README/MAPPING lines
    that mention alert( (found by searching, not hardcoded)."""
    m = site.model
    patched = [(l, n) for l, n in j.alerts_patched.items() if n]
    lines = _read_lines(site, JUDGE_README)
    quotes = []
    for i, line in enumerate(lines):
        if "alert(" not in line or not re.match(r"^\s*[-*]\s", line):
            continue
        ind = len(line) - len(line.lstrip())
        subs = []
        for k in range(i + 1, len(lines)):
            s = lines[k]
            if not s.strip() or len(s) - len(s.lstrip()) <= ind:
                break
            subs.append((k + 1, s))
        mine = [(n, s) for n, s in subs if f"**{j.label.lower()} judge**" in s.lower()]
        if patched or mine:
            quotes.append(_quote(site, JUDGE_README, (i + 1, line), "Judge/README.md"))
            quotes.extend(_quote(site, JUDGE_README, h, "Judge/README.md") for h in mine)
    if "MAPPING.md" in j.files:
        for i, line in enumerate(_read_lines(site, j.files["MAPPING.md"]), 1):
            if "alert(" in line:
                quotes.append(_quote(site, j.files["MAPPING.md"], (i, line), "MAPPING.md"))
    if not patched and not quotes:
        return ""
    items = "".join(
        f'<li>{_rv(f"<strong>{esc(l)}</strong>", f"<strong>{esc(l)}</strong> = " + cand_link(m.cand(j.mapping[l])))}: '
        f'{n} <code>alert(</code> call{"s" if n != 1 else ""} rewritten in the served copy</li>' for l, n in patched)
    lead = (f'<p>From {site.evidence(JUDGE_MAPPING, "Judge/judge-mapping.json")} (<code>alerts_patched</code>):</p><ul>{items}</ul>'
            if patched else
            f'<p>This judge got unpatched files: <code>alerts_patched</code> is 0 for every letter in '
            f'{site.evidence(JUDGE_MAPPING, "Judge/judge-mapping.json")}.</p>')
    return f"""
<section aria-labelledby="dialogs">
<h2 id="dialogs">Native dialogs</h2>
{lead}
{"".join(quotes)}
</section>"""


def _agreement(site: Site, j: Judge) -> str:
    others = [o for o in site.model.judges if o.id != j.id]
    if not others:
        return ""
    rows = []
    for o in others:
        tau, n = site.model.kendall(j, o)
        val = "–" if tau is None else f"{tau:.2f}"
        rows.append(f'<tr><th scope="row"><a href="{judge_url(o)}">{esc(o.label)}</a></th><td class="num">{val}</td><td class="num">{n}</td></tr>')
    return f"""
<section aria-labelledby="agreement">
<h2 id="agreement">Agreement with the other judges <span class="derived">derived</span></h2>
<p class="small">Kendall τ-b between this judge's ranking and each other judge's, over the candidates both ranked:
(concordant − discordant pairs) / √((pairs not tied in A) × (pairs not tied in B)). 1 = identical order, −1 = reversed.
Computed by the site build from the rankings; not part of any judge's output.</p>
<div class="table-wrap jr-narrow"><table>
<thead><tr><th scope="col">Other judge</th><th scope="col" class="num">τ-b</th><th scope="col" class="num">Common candidates</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
</section>"""


def build_judge(site: Site, j: Judge) -> None:
    m = site.model
    rp = j.files["RANKING.md"]
    url = judge_url(j)
    letters = sorted(j.mapping)
    name = lambda l: m.cand(j.mapping[l]).name
    rv_letter = lambda l: _rv(f'<strong class="jr-letter">{esc(l)}</strong>',
                              f'<a href="{cand_url(m.cand(j.mapping[l]))}">{esc(name(l))}</a>')

    def at(heading: str) -> tuple[str, int | None]:
        n = _line_no(j.md, heading)
        return (f"#L{n}" if n else ""), n

    # facts
    material = _md_cell(j.material, JUDGE_README, site) if j.material else "—"
    focus = _md_cell(j.focus, JUDGE_README, site) if j.focus else "—"
    facts = f"""<dl class="facts">
<dt>Material</dt><dd>{material}</dd>
<dt>Special-elements focus</dt><dd>{focus}</dd>
<dt>Mode</dt><dd>{_mode(j)} {"hands-on in a browser" if j.browser else "static material only"}</dd>
<dt>Candidates</dt><dd>{len(j.rows)} ranked, labelled {esc(_letters_text(letters))}</dd>
<dt>Agent log</dt><dd>{_transcript_link(site, j.files, "TRANSCRIPT.md")}</dd>
</dl>"""

    # prompt
    prompt = ""
    if "PROMPT.txt" in j.files:
        ptxt = "\n".join(_read_lines(site, j.files["PROMPT.txt"]))
        prompt = f"""
<section aria-labelledby="prompt">
<h2 id="prompt">Prompt</h2>
<p>The exact prompt the judge received, saved before launch. {site.evidence(j.files["PROMPT.txt"], "PROMPT.txt")}</p>
<details class="fold"><summary>Show the full prompt ({len(ptxt.splitlines())} lines)</summary>
<pre class="jr-prompt"><code>{esc(ptxt)}</code></pre></details>
</section>"""

    # ranking table
    a, n = at("## Ranking")
    rrows = []
    for r in j.rows:
        rrows.append(f'<tr><td class="num jr-rank">{r.rank}</td><td class="jr-cand">{rv_letter(r.letter)}</td>'
                     f'<td>{prompt_badge(r.prompt)}</td><td class="jr-just">{_md_cell(r.justification, rp, site)}</td></tr>')
    ranking = f"""
<section aria-labelledby="ranking">
<h2 id="ranking">Ranking</h2>
<p class="small muted">Best to worst, justifications verbatim. {site.evidence(rp, "RANKING.md", anchor=a, line=n)}</p>
<div class="table-wrap"><table class="jr-ranking">
<thead><tr><th scope="col" class="num">Rank</th><th scope="col">Candidate</th><th scope="col">Prompt</th><th scope="col">Justification</th></tr></thead>
<tbody>{"".join(rrows)}</tbody></table></div>
</section>"""

    # revealed mapping (always server-rendered: the no-JS fallback and the evidence)
    any_alert = any(j.alerts_patched.values())
    mrows = []
    for l in letters:
        c = m.cand(j.mapping[l])
        alert = f'<td class="num">{j.alerts_patched.get(l, 0)}</td>' if any_alert else ""
        mrows.append(f'<tr><th scope="row" class="jr-letter">{esc(l)}</th><td>{cand_link(c)}</td><td><code>{esc(c.folder)}</code></td>'
                     f'<td>{prompt_badge(j.letter_prompt[l])}</td><td class="num">{j.rank.get(c.slug, "–")}</td>{alert}</tr>')
    fc = ""
    if "MAPPING.md" in j.files:
        mtxt = "\n".join(_read_lines(site, j.files["MAPPING.md"]))
        chk = section(mtxt, "Format check")
        if chk:
            cn = _line_no(mtxt, "## Format check")
            fc = (f'<div class="jr-check"><p class="small"><strong>Automated format check</strong>, verbatim from '
                  f'{site.evidence(j.files["MAPPING.md"], "MAPPING.md", anchor=f"#L{cn}" if cn else "", line=cn)}:</p>'
                  f'{render_md(site, j.files["MAPPING.md"], text=chk, heading_ids=False)}</div>')
    mapping_link = site.evidence(j.files["MAPPING.md"], "MAPPING.md") if "MAPPING.md" in j.files else ""
    mapping = f"""
<section aria-labelledby="mapping">
<h2 id="mapping">Revealed mapping</h2>
<p class="small">Which candidate stood behind each letter. The judge never saw this; it comes from
{site.evidence(JUDGE_MAPPING, "Judge/judge-mapping.json")}{" and " + mapping_link if mapping_link else ""}.</p>
<div class="table-wrap jr-narrow"><table class="jr-mapping">
<thead><tr><th scope="col">Letter</th><th scope="col">Candidate</th><th scope="col">Folder</th><th scope="col">Prompt</th>
<th scope="col" class="num">Judge's rank</th>{'<th scope="col" class="num">alert( patched</th>' if any_alert else ""}</tr></thead>
<tbody>{"".join(mrows)}</tbody></table></div>
{fc}
</section>"""

    # criteria, special elements, summary
    a_c, n_c = at("## Ranking criteria")
    criteria = f"""
<section aria-labelledby="criteria">
<h2 id="criteria">Ranking criteria</h2>
<p class="small muted">The judge's own criteria, verbatim. {site.evidence(rp, "RANKING.md", anchor=a_c, line=n_c)}</p>
{render_md(site, rp, text=j.criteria_md, heading_ids=False)}
</section>"""
    a_s, n_s = at("## Special elements")
    sp = []
    for s in j.special:
        chips = "".join(f'<span class="chip jr-chip">{_rv(f"<strong class=jr-letter>{esc(l)}</strong>", f"<strong class=jr-letter>{esc(l)}</strong> = " + cand_link(m.cand(j.mapping[l])))}</span>' for l in s.letters)
        sp.append(f'<li><div class="jr-sp-text">{_md_cell(s.raw, rp, site)}</div><div class="jr-sp-who" aria-label="Credited candidates">{chips}</div></li>')
    special = f"""
<section aria-labelledby="special">
<h2 id="special">Special elements</h2>
<p class="small muted">Verbatim, one bullet per element. The chips name the credited letters (revealed: candidates).
{site.evidence(rp, "RANKING.md", anchor=a_s, line=n_s)} · <a href="@/techniques/">All special elements by technique</a></p>
<ul class="jr-special">{"".join(sp)}</ul>
</section>""" if sp else ""
    a_y, n_y = at("## Summary of tests and approach")
    summary = f"""
<section aria-labelledby="summary">
<h2 id="summary">Summary of tests and approach</h2>
<p class="small muted">Verbatim. {site.evidence(rp, "RANKING.md", anchor=a_y, line=n_y)}</p>
{render_md(site, rp, text=j.summary_md, heading_ids=False)}
</section>"""

    # screenshots
    shots = ""
    if j.shots:
        figs = []
        for s in j.shots:
            f = figure(site, s)
            if s.slug:
                f = f.replace("</figcaption>", f'<span class="reveal-label jr-shot-name">{esc(m.cand(s.slug).name)}</span></figcaption>', 1)
            figs.append(f)
        sdir = f"{j.dir}/screenshots"
        shots = f"""
<section aria-labelledby="screenshots">
<h2 id="screenshots">Screenshots <span class="muted jr-count">{len(j.shots)}</span></h2>
<p class="small muted">Taken by the judge; file names start with the letter it saw. {site.evidence(sdir, sdir + "/")}</p>
<div class="gallery">{"".join(figs)}</div>
</section>"""

    ev = [site.evidence(rp, "RANKING.md")]
    for k in ("MAPPING.md", "PROMPT.txt", "TRANSCRIPT.md"):
        if k in j.files:
            ev.append(site.evidence(j.files[k], k))
    ev.append(site.evidence(JUDGE_MAPPING, "judge-mapping.json"))
    ev.append(site.evidence(JUDGE_README, "Judge/README.md"))
    evidence = f"""
<section aria-labelledby="evidence">
<h2 id="evidence">Evidence</h2>
<ul class="jr-ev">{"".join(f"<li>{e}</li>" for e in ev)}</ul>
<p class="small"><a href="@/judges/">All judges and reviews</a> · <a href="@/rankings/">Combined rankings</a></p>
</section>"""

    toc = [("criteria", "Criteria"), ("ranking", "Ranking"), ("mapping", "Mapping")]
    if special:
        toc.append(("special", "Special elements"))
    toc.append(("summary", "Summary"))
    if shots:
        toc.append(("screenshots", "Screenshots"))
    if prompt:
        toc.append(("prompt", "Prompt"))
    body = f"""
<header class="jr-head">
<p class="jr-eyebrow">Phase 2 · {esc(j.label)} judge</p>
<h1>{esc(j.title)}</h1>
{facts}
</header>
{_toc(toc)}
<div class="reveal-scope" id="reveal-scope" data-reveal-scope>
{_toggle("reveal-scope", f"Blind view: letters {_letters_text(letters)} as the judge saw them.",
         "Revealed: candidate names from Judge/judge-mapping.json.")}
{criteria}
{ranking}
{mapping}
{special}
{summary}
{shots}
{_alert_quotes(site, j)}
</div>
{prompt}
{_agreement(site, j)}
{evidence}
"""
    site.page(_rel(url), f"{j.label} judge", body, section="judges",
              crumbs=[("Judges & reviews", "judges/"), (f"{j.label} judge", "")], scripts=SCRIPTS,
              description=f"Blind ranking by the {j.label} judge, with criteria, special elements and the revealed letter mapping.")

    # search documents
    path = url.removeprefix("@/")
    rank_text = [md.to_text(j.criteria_md)]
    for r in j.rows:
        rank_text.append(f"{r.rank}. {r.letter} ({name(r.letter)}, {r.prompt}): {md.to_text(r.justification)}")
    for s in j.special:
        rank_text.append(md.to_text(s.raw) + " — " + ", ".join(f"{l} = {name(l)}" for l in s.letters))
    site.search_doc(path, f"{j.label} judge — ranking", "ranking", j.title, "\n".join(rank_text))
    site.search_doc(path + "#summary", f"{j.label} judge — summary of tests and approach", "summary", j.title,
                    md.to_text(j.summary_md))


# ---------------------------------------------------------------- one review

def build_review(site: Site, r: Review) -> None:
    m = site.model
    c = m.cand(r.slug)
    url = review_url(r)
    rp = r.files["REVIEW.md"]
    # the H1 is rendered as the page header; drop that one line from the Markdown body
    lines = r.md.splitlines()
    h1_at = next((i for i, l in enumerate(lines) if l.startswith("# ")), None)
    body_md = "\n".join(lines[:h1_at] + lines[h1_at + 1:]) if h1_at is not None else r.md
    n = _line_no(r.md, r.overall_line)
    bid = r.blind_id or "–"
    reveal_name = f'<a href="{cand_url(c)}">{esc(c.name)}</a>'

    others = []
    for tid, _, label in m.review_types:
        o = m.review(tid, r.slug)
        if o and o is not r:
            others.append(f'<li><a href="{review_url(o)}">{esc(label)} review</a> '
                          f'<span class="muted">· overall {esc(fmt_score(o.overall))}</span></li>')

    prompt = ""
    if "PROMPT.txt" in r.files:
        ptxt = "\n".join(_read_lines(site, r.files["PROMPT.txt"]))
        prompt = f"""
<section aria-labelledby="prompt">
<h2 id="prompt">Prompt</h2>
<p>The exact prompt the reviewer received. {site.evidence(r.files["PROMPT.txt"], "PROMPT.txt")}</p>
<details class="fold"><summary>Show the full prompt ({len(ptxt.splitlines())} lines)</summary>
<pre class="jr-prompt"><code>{esc(ptxt)}</code></pre></details>
</section>"""

    shots = ""
    if r.shots:
        shots = f"""
<section aria-labelledby="screenshots">
<h2 id="screenshots">Screenshots <span class="muted jr-count">{len(r.shots)}</span></h2>
<div class="gallery">{"".join(figure(site, s) for s in r.shots)}</div>
</section>"""

    links = [f'<li>Candidate page: {cand_link(c)} {prompt_badge(c.prompt)}</li>']
    if others:
        links.append(f'<li>Other reviews of this candidate:<ul>{"".join(others)}</ul></li>')
    if "TRANSCRIPT.md" in r.files:
        links.append(f'<li>Review agent log: {site.evidence(r.files["TRANSCRIPT.md"], "TRANSCRIPT.md")}</li>')
    links.append(f'<li>Review folder: {site.evidence(r.dir, r.dir + "/")}</li>')
    links.append(f'<li>Blind mapping: {site.evidence(BLIND_MAPPING, "ReviewOrchestrator/blind-mapping.json")}</li>')
    links.append(f'<li>Builder chat transcript: {site.evidence(c.transcription, "TRANSCRIPTION.md")}</li>')

    status_off = f"Blind view: {bid}, as the reviewer saw it."
    status_on = "Revealed: candidate from ReviewOrchestrator/blind-mapping.json."
    body = f"""
<div class="reveal-scope" id="reveal-scope" data-reveal-scope>
<header class="jr-head">
<p class="jr-eyebrow">Phase 1 · {esc(r.type_label)} review</p>
<h1>{esc(r.title)}{_rv("", f'<span class="jr-h1-reveal"><span class="sr-only"> is </span>{esc(c.name)}</span>')}</h1>
{_toggle("reveal-scope", status_off, status_on)}
<dl class="facts">
<dt>Blind id</dt><dd><code>{esc(bid)}</code> (what the reviewer was told)</dd>
<dt>Candidate</dt><dd>{_rv('<span class="muted">hidden in blind view</span>', f'{reveal_name} · <code>{esc(c.folder)}</code>')}</dd>
<dt>Prompt</dt><dd>{prompt_badge(c.prompt)}</dd>
<dt>Review type</dt><dd>{esc(r.type_label)} ({site.evidence(f"Review/{r.type_folder}", f"Review/{r.type_folder}/")})</dd>
</dl>
<p class="note small nojs-only">Revealed mapping: <code>{esc(bid)}</code> = {reveal_name} (<code>{esc(c.folder)}</code>), from
{site.evidence(BLIND_MAPPING, "ReviewOrchestrator/blind-mapping.json")}.</p>
</header>
<section aria-labelledby="overall" class="jr-overall card">
<h2 id="overall" class="sr-only">Overall score</h2>
<p class="jr-score-big"><span class="jr-score-num">{esc(fmt_score(r.overall))}</span><span class="jr-score-of">/ 10</span>
<span class="jr-score-lbl">overall score</span></p>
<div class="jr-score-src"><p class="small muted">Parsed as the first number of this line, verbatim:</p>
<p><code class="jr-line">{esc(r.overall_line)}</code></p>
<p class="small">{site.evidence(rp, f"REVIEW.md, line {n}" if n else "REVIEW.md", anchor=f"#L{n}" if n else "", line=n)}</p></div>
</section>
</div>
<section aria-labelledby="review">
<h2 id="review">Review, verbatim</h2>
<p class="small muted">The reviewer's REVIEW.md as written (its heading is shown above). {site.evidence(rp, "REVIEW.md")}</p>
<div class="jr-review">{render_md(site, rp, text=body_md, id_prefix="r-")}</div>
</section>
{shots}
{prompt}
<section aria-labelledby="links">
<h2 id="links">Links</h2>
<ul class="jr-ev">{"".join(links)}</ul>
</section>
"""
    site.page(_rel(url), f"{r.title}", body, section="judges",
              crumbs=[("Judges & reviews", "judges/"), ("Reviews", "reviews/"), (r.title, "")], scripts=SCRIPTS,
              description=f"Blind phase-1 {r.type_label} review ({bid}): overall {fmt_score(r.overall)} / 10, verbatim.")
    site.search_doc(url.removeprefix("@/"), f"{r.type_label} review — {c.name}", "review",
                    f"Phase-1 review · {bid} · overall {fmt_score(r.overall)}", md.to_text(r.md))


# ---------------------------------------------------------------- entry point

def build(site: Site) -> None:
    build_judges_index(site)
    build_reviews_index(site)
    for j in site.model.judges:
        build_judge(site, j)
    for r in site.model.reviews:
        build_review(site, r)
