"""Special-elements catalog: techniques/ (one page).

Every bullet of every judge's "## Special elements" section (data.Judge.special) is quoted verbatim,
grouped by technique and cross-linked to the candidates it names. The technique taxonomy is the
ordered TECHNIQUES rule list below: a bullet's primary technique is the first rule whose pattern
matches its bold label, or, if no rule matches the label, the first rule matching the whole bullet;
anything still unmatched lands in "Other", so a new judge's bullets always appear. Other rules that
match the label are shown as secondary tags. The page never classifies a bullet as positive or negative.

The #mismatches section collects, by regex and verbatim, what the transcript-reading judges (judge id
contains the part "transcript") and the transcript-type phase-1 reviews (type id contains "transcript")
say about claims versus code: matching special elements, ranking justifications and review lines, plus
each such review's honesty criterion reason. Judges, review types, letters and candidates are discovered.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .. import md
from ..fragments import cand_url, judge_url, md_link, review_url, score_heat
from ..layout import Site, esc

ORDER = 500

PAGE = "techniques/index.html"
URL = "techniques/"
DERIVED = '<span class="derived">derived</span>'


@dataclass(frozen=True)
class Technique:
    id: str
    name: str
    desc: str
    pattern: str          # regex (Python syntax), searched case-insensitively unless it sets its own flags


# Matching order (first match wins). Specific rules come before broad ones, e.g. the projection-layer
# patch before the session rule, session setup before stereo/AR (its label mentions Cardboard and
# hit-test), native dialogs before AR ("VR/AR is not supported"), raymarching before defects.
TECHNIQUES: list[Technique] = [
    Technique("perturbation", "Perturbation deep zoom",
              "A high-precision reference orbit computed on the CPU, with low-precision deltas iterated on the GPU, to zoom past float32 limits.",
              r"perturbation|reference orbit|Zhuoran|rebasing"),
    Technique("projection-layer", "Projection-layer workaround",
              "Changing how three.js uses WebXR projection layers when the session does not grant the layers feature.",
              r"createProjectionLayer|monkey-patch|projection[- ]layer"),
    Technique("three-xr", "three.xr.js substitution",
              "How the archived three.xr.js library named in the v0 prompt was handled and explained.",
              r"three\.xr\.js"),
    Technique("honesty", "Claims, honesty and calibration",
              "What the assistant claimed compared with what it verified: overclaims, corrections, completion statements and explicit limits.",
              r"claim|✅|(?-i:Not verified)|certify|honest|transparent|unexplained|open issue|\bcited\b|unsupported|halluc"),
    Technique("alert", "Native dialogs",
              "Blocking browser dialogs such as alert().",
              r"alert\(|native dialog"),
    Technique("build-errors", "First-delivery build errors",
              "Deliveries that did not run on the first attempt.",
              r"compile error|broken first delivery|first build"),
    Technique("delivery", "Delivery and handoff",
              "How and when the file reached the user: turns, continuations and delivery problems.",
              r"deliver|multi-turn|handoff|no visible reply"),
    Technique("verification", "Verification practice",
              "Tests, harnesses, prototypes and emulator checks described in the transcripts.",
              r"verif|prototyped|prototyping|harness|emulator|accuracy check|compareWithCPU|Newton|\btested\b"),
    Technique("xr-session", "XR session setup and capability messaging",
              "Requested session features, per-mode fallbacks and how XR support is explained on devices without it.",
              r"session setup|local-floor|dom-overlay|capabilit|XR info|Step inside"),
    Technique("stereo", "Cardboard and split-screen stereo",
              "Side-by-side stereo views for phones without WebXR, such as iPhones.",
              r"cardboard|stereo|split-screen|side-by-side"),
    Technique("ar", "AR placement and modes",
              "Hit-test placement, AR modes and how the room behaves in AR.",
              r"(?-i:(?<!/)\bAR\b)|hit-test|passthrough"),
    Technique("gaze", "Gaze-dwell input",
              "Selecting by looking at a control for a while, for headsets without controllers or hand tracking.",
              r"gaze|dwell"),
    Technique("tours", "Guided tours and zoom flights",
              "Animated flights to named destinations in the set.",
              r"\btours?\b|destination|flights?\b"),
    Technique("gpu", "Workers, GPU pipelines and readback",
              "Moving fractal computation off the main thread, GPU textures and GPU-to-CPU readback.",
              r"worker|half-float|readback|\bPBO\b|vertex shader|fenceSync"),
    Technique("xr-input", "Hand tracking and XR input",
              "Controllers, thumbsticks, hand-tracking gestures and locomotion.",
              r"XR input|thumbstick|controller|hand[- ]tracking|hand-joint|pinch|joystick|locomotion"),
    Technique("audio", "Audio",
              "Sound tied to the experience.",
              r"audio|sound|drone"),
    Technique("mandelbulb", "Mandelbulb and other fractal modes",
              "Fractals other than the Mandelbrot set, such as the 3D Mandelbulb.",
              r"mandelbulb"),
    Technique("julia", "Julia-set inset",
              "A Julia set for the point under the pointer.",
              r"julia"),
    Technique("raymarch", "Full-screen raymarching",
              "Rendering the scene with a full-screen ray marcher.",
              r"raymarch"),
    Technique("cdn", "Runtime dependencies (CDN)",
              "Libraries loaded from the network at runtime.",
              r"\bCDNs?\b|offline|runtime network"),
    Technique("defects", "Rendering and logic defects",
              "Specific visual or logic bugs listed as special elements.",
              r"mirrored|misuse|\bbug\b|broken|not adapted|reversed"),
    Technique("ui", "In-world UI and navigation aids",
              "Panels, signage, wall screens and maps placed inside the 3D room.",
              r"panel|signage|wall[- ]screen|minimap|in-world|tablet|\bmap\b"),
]
OTHER = Technique("other", "Other", "Bullets that no rule above matches.", r"(?!)")

# Display order (thematic). Techniques missing here are appended in rule order; Other comes last.
DISPLAY = ["perturbation", "raymarch", "mandelbulb", "julia", "tours", "gpu", "xr-session", "projection-layer",
           "three-xr", "stereo", "ar", "xr-input", "gaze", "ui", "audio", "cdn", "alert", "defects",
           "build-errors", "delivery", "verification", "honesty"]

# Claims-vs-code extraction (verbatim lines/bullets/cells that match; conservative, may miss items).
MISMATCH_RE = re.compile(
    r"claim|overclaim|promis|advertis|halluc|unsupported|unverified|not implemented|never (?:ran|tested|verified)"
    r"|says .* but|false|contradict|mismatch|✅", re.I)
HONESTY_CRITERION = re.compile(r"honest", re.I)
_CODE_SPAN = re.compile(r"`[^`]*`")


def _mentions_claims(text: str) -> bool:
    """MISMATCH_RE over the text with inline code spans removed (log output such as `mismatch: 0` or
    `presenting False` is not a statement about claims)."""
    return bool(MISMATCH_RE.search(_CODE_SPAN.sub(" ", text)))


def _rx(t: Technique) -> re.Pattern:
    return re.compile(t.pattern, re.I)


_RX = {t.id: _rx(t) for t in TECHNIQUES}


# ---------------------------------------------------------------- assignment

@dataclass
class Item:
    judge: object         # data.Judge
    n: int                # 1-based position in the judge's Special elements list
    s: object             # data.Special
    primary: str = ""     # technique id
    via: str = ""         # "label" | "bullet" | "none"
    tags: list[str] = field(default_factory=list)

    @property
    def anchor(self) -> str:
        return f"b-{self.judge.id.replace('_', '-')}-{self.n}"


def classify(s) -> tuple[str, str, list[str]]:
    """(primary technique id, matched on 'label'|'bullet'|'none', secondary tag ids) for a Special."""
    on_label = [t.id for t in TECHNIQUES if _RX[t.id].search(s.title)]
    if on_label:
        return on_label[0], "label", on_label[1:]
    for t in TECHNIQUES:
        if _RX[t.id].search(s.raw):
            return t.id, "bullet", []
    return OTHER.id, "none", []


def assign(site: Site) -> list[Item]:
    items = []
    for j in site.model.judges:
        for n, s in enumerate(j.special, 1):
            p, via, tags = classify(s)
            items.append(Item(j, n, s, p, via, tags))
    return items


def _display_order() -> list[Technique]:
    by = {t.id: t for t in TECHNIQUES}
    out = [by[i] for i in DISPLAY if i in by]
    out += [t for t in TECHNIQUES if t.id not in DISPLAY]
    return out + [OTHER]


# ---------------------------------------------------------------- helpers

def _line_of(text: str, needle: str) -> int | None:
    needle = needle.strip()[:60]
    if not needle:
        return None
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


def _ev(site: Site, path: str, label: str, line: int | None) -> str:
    return site.evidence(path, label + (f", line {line}" if line else ""), anchor=f"#L{line}" if line else "", line=line)


def _inline(site: Site, src: str, text: str) -> str:
    return md.render_inline(text, link=md_link(site, src))


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _cand_rank_key(site: Site):
    order = {c.slug: i for i, c in enumerate(site.model.ordered())}
    return lambda slug: order.get(slug, 10**6)


def _letters_html(site: Site, it: Item) -> str:
    m = site.model
    parts = []
    for L, slug in zip(it.s.letters, it.s.slugs):
        c = m.cand(slug)
        parts.append(f'<span class="tq-map"><strong class="tq-letter">{esc(L)}</strong> → '
                     f'<a href="{cand_url(c)}">{esc(c.label)}</a></span>')
    return "; ".join(parts)


# ---------------------------------------------------------------- sections

def _bullet(site: Site, it: Item, by_id: dict[str, Technique]) -> str:
    j = it.judge
    p = j.files["RANKING.md"]
    line = _line_of(j.md, it.s.raw)
    tags = ""
    if it.tags:
        links = "".join(f'<a class="chip" href="#t-{t}">{esc(by_id[t].name)}</a>' for t in it.tags)
        tags = f'<p class="tq-tags small"><span class="muted">Label also matches:</span> {links}</p>'
    return f"""<li id="{it.anchor}"><blockquote class="quote"><p>{_inline(site, p, it.s.raw)}</p>
<cite><a href="{judge_url(j)}">{esc(j.label)} judge</a> · {_letters_html(site, it)} · {_ev(site, p, "RANKING.md", line)}</cite></blockquote>{tags}</li>"""


def _technique_section(site: Site, t: Technique, prim: list[Item], sec: list[Item], by_id: dict[str, Technique]) -> str:
    m = site.model
    rk = _cand_rank_key(site)
    credits: dict[str, int] = {}
    for it in prim:
        for slug in dict.fromkeys(it.s.slugs):
            credits[slug] = credits.get(slug, 0) + 1
    judges = list(dict.fromkeys(it.judge.id for it in prim))
    chips = "".join(
        f'<a class="chip tq-chip" href="{cand_url(m.cand(s))}">{esc(m.cand(s).label)}'
        f'<span class="tq-n"> ×{n}</span><span class="sr-only"> ({_plural(n, "bullet")})</span></a>'
        for s, n in sorted(credits.items(), key=lambda kv: rk(kv[0])))
    stats = (f'{_plural(len(prim), "bullet")} from {_plural(len(judges), "judge")} · '
             f'{_plural(len(credits), "candidate")} named')
    body = "".join(_bullet(site, it, by_id) for it in prim)
    also = ""
    if sec:
        li = "".join(
            f'<li><a href="#{it.anchor}">{esc(it.judge.label)} judge: “{esc(md.to_text(it.s.title).strip())}”</a> '
            f'<span class="muted">(under {esc(by_id[it.primary].name)})</span></li>' for it in sec)
        also = f'<h3 class="tq-also-h">Also tagged with this technique</h3><ul class="tq-also small">{li}</ul>'
    listing = f'<ol class="tq-bullets">{body}</ol>' if prim else '<p class="muted">No bullet has this as its primary technique.</p>'
    return f"""<section class="tq-sec" aria-labelledby="t-{t.id}">
<h2 id="t-{t.id}">{esc(t.name)}</h2>
<p class="tq-desc">{esc(t.desc)}</p>
<p class="small muted tq-stats">{stats}</p>
{f'<p class="tq-chips" aria-label="Candidates named, in order of mean rank">{chips}</p>' if chips else ''}
{listing}
{also}
</section>"""


def _matrix(site: Site, techs: list[Technique], prim: dict[str, list[Item]]) -> str:
    m = site.model
    cands = m.ordered()
    head = "".join(f'<th scope="col" class="num tq-c"><a href="{cand_url(c)}">{_head_label(c.label)}</a></th>' for c in cands)
    hi = max((sum(1 for it in prim.get(t.id, []) if c.slug in it.s.slugs) for t in techs for c in cands), default=1)
    rows, col_tot = [], {c.slug: 0 for c in cands}
    for t in techs:
        items = prim.get(t.id, [])
        if not items:
            continue
        cells = []
        for c in cands:
            n = sum(1 for it in items if c.slug in it.s.slugs)
            col_tot[c.slug] += n
            if n:
                cells.append(f'<td class="num tq-c tq-hit" style="{_count_heat(n, hi)}"><a href="#t-{t.id}" aria-label="{esc(t.name)}: {esc(c.label)}, '
                             f'{_plural(n, "mention")}">{n}</a></td>')
            else:
                cells.append('<td class="num tq-c tq-none"><span aria-hidden="true">–</span><span class="sr-only">none</span></td>')
        rows.append(f'<tr><th scope="row"><a href="#t-{t.id}">{esc(t.name)}</a></th>{"".join(cells)}'
                    f'<td class="num tq-tot">{len(items)}</td></tr>')
    foot = "".join(f'<td class="num tq-c tq-tot">{col_tot[c.slug]}</td>' for c in cands)
    total = sum(len(v) for v in prim.values())
    note = (f'<span class="muted tq-scroll-note"> The table shows {_plural(len(rows), "technique")} × '
            f'{_plural(len(cands), "candidate")}; scroll inside it, sideways and down.</span>')
    return f"""<p class="small tq-legend-p">{_count_legend(hi)}{note}</p>
<div class="table-wrap matrix-wrap tq-matrix-wrap" tabindex="0" role="region" aria-label="Candidate by technique matrix (scrolls)">
<table class="tq-matrix">
<caption>Mentions: the number of special-element bullets naming each candidate, by primary technique. These are counts of
mentions, not ratings: a bullet may describe a strength or a problem. Columns in order of mean rank {DERIVED}
(the average of the judges’ ranks; left = best). A bullet that names several candidates counts once for each; the Bullets column counts each bullet once.</caption>
<thead><tr><th scope="col">Technique</th>{head}<th scope="col" class="num">Bullets</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
<tfoot><tr><th scope="row">Bullets naming the candidate <span class="derived">derived</span><span class="sr-only"> (sum of the column)</span></th>{foot}<td class="num tq-tot">{total}</td></tr></tfoot>
</table></div>"""


def _head_label(label: str) -> str:
    """Column header: the model part may wrap; the trailing ' · <variant>' goes on its own line as just
    '<variant>' (no stray middot at the line start; the separator stays in the accessible name)."""
    name, sep, var = label.rpartition(" · ")
    if not sep:
        return esc(label)
    return f'{esc(name)}<span class="sr-only"> · </span> <span class="tq-cv">{esc(var)}</span>'


def _count_heat(n: int, hi: int) -> str:
    """Single-hue fill for a mention count, the same blue scale as the score heatmaps; 1 is faintest, hi strongest."""
    return score_heat(n, 0, max(1, hi))


def _count_legend(hi: int) -> str:
    sw = "".join(f'<span class="heat-swatch" style="{_count_heat(n, hi)}">{n}</span>' for n in range(1, hi + 1))
    return (f'<span class="legend-scale tq-legend"><span>Shading strengthens with the number of mentions:</span>'
            f'<span class="heat-swatches" aria-hidden="true">{sw}</span></span>')


def _index_item(t: Technique, n: int) -> str:
    """Index entry; the count stays on the line of the label's last word."""
    head, _sp, last = t.name.rpartition(" ")
    return (f'<li><a href="#t-{t.id}">{esc(head) + " " if head else ""}<span class="tq-nw">{esc(last)}</span></a>'
            f'<span class="tq-nw"> <span class="muted small tq-idx-n">{n}</span></span></li>')


def _rules_details() -> str:
    li = "".join(f'<li><strong>{esc(t.name)}</strong> <code>{esc(t.pattern)}</code></li>' for t in TECHNIQUES)
    return f"""<details class="fold tq-rules"><summary>How bullets are assigned (rules, in matching order)</summary>
<p class="small">Each bullet gets exactly one primary technique: the first rule below whose pattern (case-insensitive regular
expression) matches the bullet’s bold label; if no rule matches the label, the first rule that matches the whole bullet;
otherwise “Other”. Further rules that match the label are shown as tags. This grouping is the site’s index, not the judges’
own categories.</p><ol class="small tq-rule-list">{li}</ol></details>"""


# ---------------------------------------------------------------- claims vs code

@dataclass
class Quote:
    slug: str
    key: tuple            # dedupe key
    order: tuple          # sort key within a candidate
    html: str


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[*_`]", "", s)).strip().lower()


def _split_row(line: str) -> list[str]:
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def _render_line(site: Site, src: str, line: str) -> str:
    s = line.strip()
    if s.startswith("|") and s.endswith("|"):
        return " · ".join(_inline(site, src, c) for c in _split_row(s) if c)
    s = re.sub(r"^#+\s+", "", s)
    s = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", s)
    return _inline(site, src, s)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def _quote_html(site: Site, src: str, body: str, children: list[str], cite: str) -> str:
    sub = ""
    if children:
        sub = '<ul class="tq-sub">' + "".join(f"<li>{_render_line(site, src, c)}</li>" for c in children) + "</ul>"
    return f'<li><blockquote class="quote"><p>{body}</p>{sub}<cite>{cite}</cite></blockquote></li>'


def _review_quotes(site: Site, r) -> list[Quote]:
    """Honesty criterion reason (always) + every matching line/bullet/cell of a review, verbatim."""
    path = r.files.get("REVIEW.md", f"{r.dir}/REVIEW.md")
    lines = r.md.splitlines()
    page = f'<a href="{review_url(r)}">{esc(r.type_label)} review</a>'
    out: list[Quote] = []
    seen_lines: set[int] = set()
    for crit in r.criteria:
        if not HONESTY_CRITERION.search(crit.name):
            continue
        n = next((i for i, l in enumerate(lines, 1) if l.strip().startswith("|") and crit.reason[:60] in l), None)
        if n:
            seen_lines.add(n)
        cite = (f'{page} · criterion “{esc(crit.name)}”, score {esc(f"{crit.score:g}")} / 10 · '
                f'{_ev(site, path, "REVIEW.md", n)}')
        out.append(Quote(r.slug, (path, _norm(crit.reason)), (1, r.type_id, n or 0),
                         _quote_html(site, path, _inline(site, path, crit.reason), [], cite)))
    consumed: set[int] = set()
    for i, line in enumerate(lines, 1):
        if i in consumed or i in seen_lines or not line.strip() or not _mentions_claims(line):
            continue
        children = []
        if _ITEM.match(line):
            k = _indent(line)
            for jx in range(i, len(lines)):
                nxt = lines[jx]
                if not nxt.strip() or _indent(nxt) <= k:
                    break
                children.append(nxt)
                consumed.add(jx + 1)
        cite = f'{page} · {_ev(site, path, "REVIEW.md", i)}'
        out.append(Quote(r.slug, (path, _norm(line)), (1, r.type_id, i),
                         _quote_html(site, path, _render_line(site, path, line), children, cite)))
    return out


def _judge_quotes(site: Site, j) -> list[Quote]:
    p = j.files["RANKING.md"]
    out: list[Quote] = []
    for n, s in enumerate(j.special, 1):
        if not _mentions_claims(s.raw):
            continue
        line = _line_of(j.md, s.raw)
        letters = ", ".join(s.letters)
        anchor = f"b-{j.id.replace('_', '-')}-{n}"
        for slug in dict.fromkeys(s.slugs):
            cite = (f'<a href="{judge_url(j)}">{esc(j.label)} judge</a>, special element for letter(s) {esc(letters)} '
                    f'(<a href="#{anchor}">in the catalog</a>) · {_ev(site, p, "RANKING.md", line)}')
            out.append(Quote(slug, (p, _norm(s.raw)), (0, j.id, line or 0),
                             _quote_html(site, p, _inline(site, p, s.raw), [], cite)))
    for row in j.rows:
        if not _mentions_claims(row.justification):
            continue
        line = _line_of(j.md, row.justification)
        cite = (f'<a href="{judge_url(j)}">{esc(j.label)} judge</a>, ranking justification '
                f'(letter {esc(row.letter)}, rank {row.rank} of {len(j.rows)}) · {_ev(site, p, "RANKING.md", line)}')
        out.append(Quote(row.slug, (p, _norm(row.justification)), (0, j.id, line or 0),
                         _quote_html(site, p, _inline(site, p, row.justification), [], cite)))
    return out


def _is_transcript(type_id: str) -> bool:
    return "transcript" in type_id.split("_")


def _mismatches(site: Site) -> tuple[str, str]:
    m = site.model
    judges = [j for j in m.judges if _is_transcript(j.id)]
    rtypes = [(tid, label) for tid, _f, label in m.review_types if _is_transcript(tid)]
    quotes: list[Quote] = []
    for j in judges:
        quotes += _judge_quotes(site, j)
    for tid, _label in rtypes:
        for c in m.candidates:
            r = m.review(tid, c.slug)
            if r:
                quotes += _review_quotes(site, r)
    by: dict[str, list[Quote]] = {}
    for q in quotes:
        lst = by.setdefault(q.slug, [])
        if any(x.key == q.key for x in lst):
            continue
        lst.append(q)
    groups, text = [], []
    for c in m.ordered():
        qs = sorted(by.get(c.slug, []), key=lambda q: q.order)
        if not qs:
            continue
        groups.append(f"""<section class="tq-mm-group" aria-labelledby="mm-{c.slug}">
<h3 id="mm-{c.slug}"><a href="{cand_url(c)}">{esc(c.label)}</a> <span class="muted small tq-mm-meta">{_plural(len(qs), "quote")}</span></h3>
<ul class="tq-quotes">{"".join(q.html for q in qs)}</ul>
</section>""")
    jl = ", ".join(f'<a href="{judge_url(j)}">{esc(j.label)}</a>' for j in judges) or "none"
    rl = []
    for tid, label in rtypes:
        rl.append(f'{esc(label)} (' + ", ".join(
            f'<a href="{review_url(r)}">{esc(m.cand(r.slug).label)}</a>'
            for c in m.ordered() if (r := m.review(tid, c.slug))) + ")")
    rls = "; ".join(rl) or "none"
    crit = ""
    if rtypes:
        crit = (" each such review’s honesty criterion reason (the criteria row whose name matches "
                f"<code>{esc(HONESTY_CRITERION.pattern)}</code>), always; and")
    html = f"""<section class="tq-mm" aria-labelledby="mismatches">
<h2 id="mismatches">Claims vs code and hallucinations</h2>
<p>What the judges and reviewers who read the chat transcripts report about the assistants’ claims compared with their
code and tests, quoted verbatim and grouped by candidate, in order of mean rank {DERIVED} (the average of the
judges’ ranks; best first).</p>
<div class="note small"><p><strong>How this list was made.</strong> It is extracted automatically, not curated. Sources: the
judges whose id contains “transcript” ({jl}) and the phase-1 reviews whose type contains “transcript” ({rls}). Included
are:{crit} every special-element bullet, ranking justification and review line, bullet or table row that matches
<code>{esc(MISMATCH_RE.pattern)}</code> (case-insensitive, ignoring text inside code spans). Sub-bullets of a matching bullet are kept with it; duplicates are
dropped. Because it is regex-based it may miss items, and it also catches statements about claims that the source
counts in an assistant’s favour. Nothing is reworded; read the full reviews and rankings through the links.</p></div>
{"".join(groups) or '<p class="muted">No matching statements.</p>'}
</section>"""
    for q in quotes:
        text.append(re.sub(r"<[^>]+>", " ", q.html))
    return html, " ".join(text)


# ---------------------------------------------------------------- page

def build(site: Site) -> None:
    m = site.model
    items = assign(site)
    techs = _display_order()
    by_id = {t.id: t for t in techs}
    prim: dict[str, list[Item]] = {}
    sec: dict[str, list[Item]] = {}
    for it in items:
        prim.setdefault(it.primary, []).append(it)
        for t in it.tags:
            sec.setdefault(t, []).append(it)
    shown = [t for t in techs if prim.get(t.id) or sec.get(t.id)]
    others = prim.get(OTHER.id, [])
    if others:
        print(f"techniques: {len(others)} special element(s) under 'Other': "
              + "; ".join(f"{it.judge.id}#{it.n}" for it in others))

    nj = sum(1 for j in m.judges if j.special)
    index = "".join(_index_item(t, len(prim.get(t.id, []))) for t in shown)
    sections = "".join(_technique_section(site, t, prim.get(t.id, []), sec.get(t.id, []), by_id) for t in shown)
    mm_html, mm_text = _mismatches(site)
    judge_links = ", ".join(f'<a href="{judge_url(j)}">{esc(j.label)}</a>' for j in m.judges if j.special)

    body = f"""<header class="tq-head">
<h1>Techniques and special elements</h1>
<p class="lede">Every bullet from every judge’s “Special elements” section — {_plural(len(items), "bullet")} from
{_plural(nj, "judge")} — quoted verbatim and grouped by technique, with the candidates each one names.</p>
<p>Letters are each judge’s own blind labels; the arrow shows the candidate the letter maps to in
{site.evidence("Judge/judge-mapping.json", "Judge/judge-mapping.json")}. Judges: {judge_links}. The bullets include both
strengths and problems, exactly as the judges wrote them; this page does not rate them. A separate section collects
<a href="#mismatches">claims vs code and hallucinations</a> reported by the transcript readers.</p>
</header>
<nav class="tq-index" aria-labelledby="tq-index-h">
<h2 id="tq-index-h" class="tq-index-h">Techniques <span class="muted small">(bullets with this primary technique)</span></h2>
<ol>{index}</ol>
<p class="small"><a href="#matrix">Candidate × technique matrix</a> · <a href="#mismatches">Claims vs code and hallucinations</a></p>
</nav>
{_rules_details()}
<section aria-labelledby="matrix">
<h2 id="matrix">Candidate × technique matrix</h2>
<p class="muted tq-matrix-p">Each cell shows how many bullets name the candidate under that primary technique (mentions);
“–” means none. These are counts of mentions, not ratings: many bullets are criticisms. The bottom row sums each column.
Select a row or a count to jump to the quotes.</p>
{_matrix(site, techs, prim)}
</section>
{sections}
{mm_html}"""
    site.page(PAGE, "Techniques", body, section="techniques", crumbs=[("Techniques", URL)],
              description="Every special element the judges noted, quoted verbatim and grouped by technique, "
                          "plus claims-vs-code mismatches reported by the transcript judges and reviews.")

    site.search_doc(URL, "Techniques and special elements", "page", "Special-elements catalog",
                    " ".join(f"{t.name}. {t.desc}" for t in shown))
    for t in shown:
        txt = " ".join(md.to_text(it.s.raw) for it in prim.get(t.id, []))
        site.search_doc(f"{URL}#t-{t.id}", f"Technique: {t.name}", "page", "Special-elements catalog",
                        f"{t.desc} {txt}")
    site.search_doc(f"{URL}#mismatches", "Claims vs code and hallucinations", "page", "Special-elements catalog",
                    re.sub(r"\s+", " ", mm_text).strip())
