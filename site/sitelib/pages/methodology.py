"""methodology/: how the experiment was run — caveats, pipeline, blinding, effort, serving,
environment limits, every incident from both READMEs, the discarded run, both prompts verbatim
(with a word-level diff), how the derived metrics are computed, and how to reproduce the pipeline.

Everything is quoted from the process record (ReviewOrchestrator/README.md, Judge/README.md, PLAN.md,
the prompt files, the tools and server logs) and linked to its source. Incidents are parsed from the
READMEs' incident sections, so a new incident appears without code changes.
"""
from __future__ import annotations

import ast
import difflib
import html
import os
import re
from collections import Counter

from .. import md
from ..data import DataError, parse_overall, section
from ..fragments import CAVEATS, fmt_mean, md_link, render_md
from ..layout import Site, cand_link, esc, prompt_badge

ORDER = 800

RO = "ReviewOrchestrator"
RO_README = f"{RO}/README.md"
J_README = "Judge/README.md"
TOOLS = f"{RO}/tools"
LOGS = f"{RO}/server-logs"
BLIND = f"{RO}/blind"

TOC = [
    ("caveats", "Caveats"),
    ("pipeline", "Pipeline"),
    ("blinding", "Blinding"),
    ("effort", "Effort deviation"),
    ("serving", "Serving"),
    ("environment", "Environment limits"),
    ("incidents", "Incidents"),
    ("discarded", "Discarded run"),
    ("prompts", "Prompts"),
    ("derived", "Derived metrics"),
    ("reproduce", "Reproducing"),
]

# Process stages and the tools that implement them (descriptive; every tool file is checked to exist,
# and tools not named here are listed automatically under "Other tools").
STAGES = [
    ("extract", "Extract", ["claude2md.py"]),
    ("blind", "Blind", ["blind.py", "judge_blind.py"]),
    ("review", "Review", ["prompts.py", "finalize.py", "jsonl2md.py", "redact.py"]),
    ("judge", "Judge", ["judge_prompts.py", "judge_finalize.py"]),
    ("aggregate", "Aggregate", ["judge_aggregate.py"]),
]

# Caveat title (fragments.CAVEATS) -> (file, phrase) anchors of the verbatim supporting sentences.
CAVEAT_SUPPORT = {
    "Two prompts": [(RO_README, "is the v0 prompt"), (J_README, "Each candidate was judged against its own prompt")],
    "No headset": [(RO_README, "no real VR or AR session was entered"), (J_README, "No real VR or AR session was entered")],
    "Same model family": [(RO_README, "did the orchestration"), (RO_README, "agents ran in parallel"),
                          (RO_README, "Five more blind agents"), (J_README, "subagent on")],
}
CAVEAT_LINKS = {
    "Two prompts": [("#prompts", "Both prompts and their diff")],
    "No headset": [("#environment", "Environment limits")],
    "Same model family": [("#blinding", "Blinding"), ("@/judges/", "Judges and reviews")],
}


# ---------------------------------------------------------------- source helpers

class Src:
    """A repo text file with line-aware lookups (all failures name the file)."""

    def __init__(self, site: Site, path: str):
        self.site, self.path = site, path
        with open(os.path.join(site.repo, path), encoding="utf-8") as f:
            self.text = f.read()
        self.lines = self.text.splitlines()

    def line_of(self, needle: str, start: int = 1) -> int:
        for i in range(start - 1, len(self.lines)):
            if needle in self.lines[i]:
                return i + 1
        raise DataError(f"{self.path}: expected text not found: {needle!r}")

    def section(self, pattern: str) -> tuple[str, int, str]:
        """(heading text, first body line number, body) of the first '## ' heading matching pattern."""
        for i, l in enumerate(self.lines):
            m = re.match(r"^##\s+(.*?)\s*$", l)
            if m and re.search(pattern, m.group(1), re.I):
                body = []
                for l2 in self.lines[i + 1:]:
                    if re.match(r"^##\s", l2):
                        break
                    body.append(l2)
                return m.group(1), i + 2, "\n".join(body).strip("\n")
        raise DataError(f"{self.path}: no '## ' section matching {pattern!r}")

    def sentence(self, phrase: str) -> tuple[str, int]:
        """The full sentence (Markdown, verbatim) containing phrase, and its line number."""
        n = self.line_of(phrase)
        line = self.lines[n - 1]
        k = line.find(phrase)
        body_start = re.match(r"^\s*(?:[-*]|\d+\.)?\s*", line).end()
        start = body_start
        for m in re.finditer(r"[.!?]\s+(?=[A-Z`*(])", line):
            if m.end() <= k:
                start = max(start, m.end())
        end = len(line)
        m = re.compile(r"[.!?](?=\s+[A-Z`*(]|\s*$)").search(line, k + len(phrase))
        if m:
            end = m.end()
        return line[start:end].strip(), n

    def ev(self, label: str | None = None, line: int | None = None) -> str:
        return self.site.evidence(self.path, label or self.path, anchor=f"#L{line}" if line else "", line=line)


def clink(c) -> str:
    """Short candidate label (tables, compact lists), linked to the candidate page."""
    return f'<a href="@/candidates/{c.slug}/">{esc(c.label)}</a>'


def _link(site: Site, path: str):
    return md_link(site, path)


def inline(site: Site, path: str, text: str) -> str:
    return md.render_inline(text, link=_link(site, path))


def quote(site: Site, src: Src, text: str, line: int, *, block: bool = False, label: str | None = None) -> str:
    body = render_md(site, src.path, text=text, heading_ids=False) if block else f"<p>{inline(site, src.path, text)}</p>"
    cite = src.ev(label or f"{src.path}, line {line}", line)
    return f'<blockquote class="quote">{body}<cite>{cite}</cite></blockquote>'


def quote_sentence(site: Site, src: Src, phrase: str, **kw) -> str:
    s, n = src.sentence(phrase)
    return quote(site, src, s, n, **kw)


def list_items(body: str, first_line: int) -> list[dict]:
    """Top-level Markdown list items of a section body: marker, number, text (dedented), line."""
    items, cur, blank = [], None, False
    for off, l in enumerate(body.splitlines()):
        m = re.match(r"^(\d+)[.)]\s+(.*)$|^[-*+]\s+(.*)$", l)
        if m:
            cur = {"num": m.group(1), "text": [m.group(2) if m.group(1) else m.group(3)],
                   "indent": (len(m.group(1)) + 2) if m.group(1) else 2, "line": first_line + off}
            items.append(cur)
            blank = False
        elif not l.strip():
            blank = True
            if cur:
                cur["text"].append("")
        elif cur and (l.startswith(" ") or l.startswith("\t") or not blank):
            ind = len(l) - len(l.lstrip(" "))
            cur["text"].append(l[min(ind, cur["indent"]):] if l.startswith(" ") else l)
        else:
            cur = None          # a paragraph after the list ends it
    for it in items:
        it["text"] = "\n".join(it["text"]).strip()
    return items


def split_lead(text: str) -> tuple[str | None, str]:
    """('Effort', rest) for an item that starts with '**Effort:** rest'."""
    m = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", text, re.S)
    if not m:
        return None, text
    return m.group(1).strip().rstrip(":").strip(), m.group(2).lstrip(":").strip()


def plain(html_text: str) -> str:
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", html_text, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def docstring(site: Site, path: str) -> str:
    try:
        with open(os.path.join(site.repo, path), encoding="utf-8") as f:
            d = ast.get_docstring(ast.parse(f.read())) or ""
    except SyntaxError:
        d = ""
    return d.strip().split("\n")[0] if d else ""


# ---------------------------------------------------------------- page sections

def sec_caveats(site: Site, srcs: dict[str, Src]) -> str:
    m = site.model
    items = []
    for title, text in CAVEATS:
        quotes = "".join(quote_sentence(site, srcs[p], ph) for p, ph in CAVEAT_SUPPORT.get(title, []))
        extra = ""
        if title == "Same model family":
            s, _ = srcs[J_README].sentence("subagent on")
            mm = re.search(r"subagent on (.+?) with effort", s)
            norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
            if mm:
                same = [c for c in m.candidates if norm(mm.group(1)) in norm(c.model)]
                if same:
                    lis = "".join(f"<li>{cand_link(c)}: model recorded as <code>{esc(c.model)}</code></li>" for c in same)
                    extra = (f'<p class="small">Candidates whose recorded model matches the judges\' model '
                             f'({esc(mm.group(1))}), from {site.evidence("site/candidates.toml", "site/candidates.toml")}:</p><ul class="small">{lis}</ul>')
        links = " · ".join(f'<a href="{esc(h)}">{esc(l)}</a>' for h, l in CAVEAT_LINKS.get(title, []))
        items.append(f'<li class="cav"><h3>{esc(title)}</h3><p class="cav-claim">{esc(text)}</p>'
                     f'<details class="fold" open><summary>Supporting sentences, verbatim</summary>{quotes}{extra}</details>'
                     + (f'<p class="small">See also: {links}</p>' if links else "") + "</li>")
    return ('<div class="caveat cav-box"><p class="cav-lead"><strong>Read every result on this site with these caveats in mind.</strong> '
            'They are stated as facts of the process, not as judgements of any candidate.</p>'
            f'<ol class="cav-list">{"".join(items)}</ol></div>')


def stage_data(site: Site) -> list[dict]:
    m = site.model
    n = len(m.candidates)
    prompts = [p for _, p in prompt_files(site)]
    tools_present = set(os.listdir(os.path.join(site.repo, TOOLS))) if os.path.isdir(os.path.join(site.repo, TOOLS)) else set()
    out = []
    outputs = {
        "extract": [(f"{n} candidate folders, each with a product .html and TRANSCRIPTION.md", None),
                    (", ".join(prompts), None)],
        "blind": [("blind-mapping.json (candidate-NN)", f"{RO}/blind-mapping.json"),
                  ("blind/: anonymized transcripts and sha256 lists", BLIND),
                  ("judge-mapping.json (letters)", "Judge/judge-mapping.json")],
        "review": [(f"{len(m.reviews)} reviews of {len(m.review_types)} types: REVIEW.md, PROMPT.txt, agent log, screenshots", "Review")],
        "judge": [(f"{len(m.judges)} judgments: RANKING.md, MAPPING.md, PROMPT.txt, agent log, screenshots", "Judge")],
        "aggregate": [("rank table in Judge/README.md", J_README), ("derived metrics on this site", None)],
    }
    for key, label, tools in STAGES:
        for t in tools:
            if t not in tools_present:
                raise DataError(f"{TOOLS}/{t}: pipeline stage {key!r} names this tool, but the file does not exist")
        out.append({"key": key, "label": label, "tools": [(t, f"{TOOLS}/{t}") for t in tools], "outputs": outputs[key]})
    return out


def wrap(text: str, width: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    return lines + ([cur] if cur else [])


def pipeline_svg(site: Site, stages: list[dict], vertical: bool) -> str:
    n = len(stages)
    width = 40 if vertical else 23
    outl = [[l for o, _ in s["outputs"] for l in wrap(o, width)] for s in stages]
    rows = max(len(s["tools"]) + len(o) for s, o in zip(stages, outl))
    lh, top, pad = 20, 54, 14
    bh = top + 22 + rows * lh + 22 + pad
    if vertical:
        W, bw, gap = 360, 360, 40
        hs = [top + 22 + (len(s["tools"]) + len(o)) * lh + 22 + pad for s, o in zip(stages, outl)]
        pos, y = [], 0
        for h in hs:
            pos.append((0, y))
            y += h + gap
        H = y - gap
    else:
        W, gap = 1200, 36
        bw = (W - gap * (n - 1)) / n
        H = bh
        hs = [bh] * n
        pos = [(i * (bw + gap), 0) for i in range(n)]
    parts = []
    for i, (s, (x, y)) in enumerate(zip(stages, pos)):
        bh = hs[i]
        parts.append(f'<g class="pl-stage"><rect class="pl-box" x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="10"/>')
        parts.append(f'<text class="pl-num" x="{x + pad:.1f}" y="{y + 28:.1f}">{i + 1}</text>'
                     f'<text class="pl-title" x="{x + pad + 22:.1f}" y="{y + 28:.1f}">{esc(s["label"])}</text>')
        cy = y + top
        parts.append(f'<text class="pl-label" x="{x + pad:.1f}" y="{cy:.1f}">TOOLS</text>')
        cy += 20
        for t, p in s["tools"]:
            parts.append(f'<text class="pl-tool" x="{x + pad:.1f}" y="{cy:.1f}">{esc(t)}</text>')
            cy += lh
        cy += 8
        parts.append(f'<text class="pl-label" x="{x + pad:.1f}" y="{cy:.1f}">OUTPUTS</text>')
        cy += 20
        for o in outl[i]:
            parts.append(f'<text class="pl-out" x="{x + pad:.1f}" y="{cy:.1f}">{esc(o)}</text>')
            cy += lh
        parts.append("</g>")
        if i < n - 1:
            if vertical:
                ax, ay = x + bw / 2, y + bh
                parts.append(f'<path class="pl-arrow" d="M{ax:.1f} {ay + 4:.1f} V{ay + gap - 8:.1f}"/>'
                             f'<path class="pl-head" d="M{ax - 7:.1f} {ay + gap - 12:.1f} L{ax:.1f} {ay + gap - 3:.1f} L{ax + 7:.1f} {ay + gap - 12:.1f} Z"/>')
            else:
                ax, ay = x + bw, y + 30
                parts.append(f'<path class="pl-arrow" d="M{ax + 4:.1f} {ay:.1f} H{ax + gap - 8:.1f}"/>'
                             f'<path class="pl-head" d="M{ax + gap - 12:.1f} {ay - 7:.1f} L{ax + gap - 3:.1f} {ay:.1f} L{ax + gap - 12:.1f} {ay + 7:.1f} Z"/>')
    cls = "pl-v" if vertical else "pl-h"
    tid = f"pl-title-{'v' if vertical else 'h'}"
    flow = " → ".join(s["label"].lower() for s in stages)
    desc = "; ".join(f'{i + 1}. {s["label"]}: tools {", ".join(t for t, _ in s["tools"])}; outputs {" ".join(o for o, _ in s["outputs"])}'
                     for i, s in enumerate(stages))
    return (f'<svg class="chart pipeline {cls}" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-labelledby="{tid} {tid}-d">'
            f'<title id="{tid}">Pipeline diagram: {esc(flow)}</title><desc id="{tid}-d">{esc(desc)}. The same content follows as a list with links.</desc>'
            + "".join(parts) + "</svg>")


def sec_pipeline(site: Site, srcs: dict[str, Src]) -> str:
    stages = stage_data(site)
    tools_dir = os.path.join(site.repo, TOOLS)
    named = {t for s in STAGES for t in s[2]}
    others = sorted(t for t in os.listdir(tools_dir) if t.endswith(".py") and t not in named) if os.path.isdir(tools_dir) else []
    ol = []
    for s in stages:
        tools = ", ".join(site.evidence(p, t) for t, p in s["tools"])
        outs = []
        for o, p in s["outputs"]:
            outs.append(f'<a href="{esc(site.local(p))}">{esc(o)}</a>' if p else esc(o))
        ol.append(f'<li><strong>{esc(s["label"])}</strong>. Tools: {tools}. Outputs: {"; ".join(outs)}.</li>')
    other = ""
    if others:
        other = ("<p class=\"small\">Other tools in <code>tools/</code> that are not a pipeline stage: "
                 + ", ".join(site.evidence(f"{TOOLS}/{t}", t) for t in others) + ".</p>")
    ro = srcs[RO_README]
    head, ln, body = ro.section(r"^\d+\.\s*Steps")
    return (f'<p>The process ran in {len(stages)} stages. Each box names the scripts that implemented it (linked to their source) and what it wrote to the repository. '
            f'The step-by-step account is {ro.ev("ReviewOrchestrator/README.md §2 “Steps”", ln - 1)}; extraction itself was done by the orchestrator in the browser, '
            f'with <code>claude2md.py</code> only for the claude.ai conversation exports.</p>'
            f'<figure class="pipeline-fig"><div class="pipeline-wrap">{pipeline_svg(site, stages, False)}{pipeline_svg(site, stages, True)}</div>'
            f'<figcaption class="small muted">Text equivalent of the diagram:</figcaption></figure>'
            f'<ol class="pipeline-list">{"".join(ol)}</ol>{other}')


def sha_lists(site: Site) -> dict[str, dict[str, str]]:
    out = {}
    d = os.path.join(site.repo, BLIND)
    for n in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if n.endswith(".sha256"):
            entries = {}
            with open(os.path.join(d, n), encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        h, _, p = line.strip().partition("  ")
                        entries[p.strip()] = h.strip()
            out[f"{BLIND}/{n}"] = entries
    return out


def sec_blinding(site: Site, srcs: dict[str, Src]) -> str:
    m = site.model
    ro, jr = srcs[RO_README], srcs[J_README]
    _, ln, body = ro.section(r"^\d+\.\s*Steps")
    steps = list_items(body, ln)
    blind_step = next((s for s in steps if "blind" in s["text"].lower() and "shuffled" in s["text"].lower()), None)
    if blind_step is None:
        raise DataError(f"{RO_README}: no step describing the blind shuffle found in §2")
    plan = srcs.get(f"{RO}/PLAN.md")

    # phase-1 table
    lists = sha_lists(site)
    flat = {}
    for f, entries in lists.items():
        for p, h in entries.items():
            flat[p] = (h, f)
    rows = []
    for nn, slug in sorted(m.blind.items()):
        c = m.cand(slug)
        idx = flat.get(f"{nn}/index.html")
        srch = flat.get(c.html_path)
        if idx and srch:
            same = idx[0] == srch[0] == c.sha256
            verdict = '<span class="ok">✓ identical</span>' if same else '<span class="bad">✗ differs</span>'
            shas = f'<code title="{esc(idx[0])}">{esc(idx[0][:12])}…</code>'
        else:
            verdict, shas = '<span class="muted">not listed</span>', "–"
        tp = f"{BLIND}/{nn}/TRANSCRIPT.md"
        seen = f'<a href="{esc(site.local(tp))}">anonymized transcript</a>' if os.path.isfile(os.path.join(site.repo, tp)) else "–"
        rows.append(f"<tr><th scope=\"row\"><code>{esc(nn)}</code></th><td>{clink(c)} {prompt_badge(c.prompt)}</td>"
                    f"<td>{shas}</td><td>{verdict}</td><td>{seen}</td></tr>")
    list_links = " and ".join(site.evidence(f, os.path.basename(f)) for f in lists)
    t1 = ('<div class="table-wrap"><table class="meth-table"><caption>Phase-1 mapping from '
          f'{site.evidence(f"{RO}/blind-mapping.json", "blind-mapping.json")}. sha256 prefix of the blind copy; '
          f'“identical” means the blind copy, the source file and the file this build copied all have the same sha256 ({list_links}).</caption>'
          '<thead><tr><th scope="col">Blind id</th><th scope="col">Candidate</th><th scope="col">Blind copy sha256</th>'
          '<th scope="col">Byte-identical</th><th scope="col">What transcript reviewers read</th></tr></thead>'
          f'<tbody>{"".join(rows)}</tbody></table></div>')

    # phase-2 table: candidates x judges -> letter
    js = m.judges
    head = "".join(f'<th scope="col"><a href="@/judges/{j.id.replace("_", "-")}/">{esc(j.label)}</a></th>' for j in js)
    body_rows = []
    for c in m.candidates:
        cells = []
        for j in js:
            letter = next((l for l, s in j.mapping.items() if s == c.slug), None)
            cells.append(f'<td class="letter">{esc(letter) if letter else "–"}</td>')
        body_rows.append(f"<tr><th scope=\"row\">{clink(c)}</th>{''.join(cells)}</tr>")
    t2 = ('<div class="table-wrap matrix-wrap" role="region" aria-label="Letters per judge: candidate × judge">'
          '<table class="meth-table letters"><caption>Letter each judge saw for each candidate, from '
          f'{site.evidence("Judge/judge-mapping.json", "judge-mapping.json")} (– = not shown to that judge).</caption>'
          f'<thead><tr><th scope="col">Candidate</th>{head}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>')

    seed_q = ""
    bsrc = Src(site, f"{TOOLS}/blind.py") if os.path.isfile(os.path.join(site.repo, TOOLS, "blind.py")) else None
    if bsrc:
        for i, l in enumerate(bsrc.lines, 1):
            if re.search(r"random\.seed\(", l):
                seed_q = (f'<p>The phase-1 seed as it appears in the code: <code>{esc(l.strip())}</code> '
                          f'({bsrc.ev(f"blind.py, line {i}", i)}).</p>')
                break
    plan_q = ""
    if plan:
        try:
            plan_q = quote_sentence(site, plan, "best effort")
        except DataError:
            plan_q = ""
    patch_q = quote_sentence(site, jr, "except for the one patch below")
    native = ""
    try:
        _, mln, mbody = jr.section(r"^Method$")
        for it in list_items(mbody, mln):
            t, _ = split_lead(it["text"])
            if t and "dialog" in t.lower():
                native = quote(site, jr, it["text"], it["line"], block=True)
    except DataError:
        pass
    return (
        '<h3>Phase 1: candidate-NN</h3>'
        + quote(site, ro, blind_step["text"], blind_step["line"], block=True,
                label=f"ReviewOrchestrator/README.md §2, step {blind_step['num']}")
        + seed_q
        + '<p>Reviewers saw only the blind id. The HTML reviewers read the copy named <code>index.html</code>; the transcript reviewers read the anonymized transcript linked in the last column.</p>'
        + t1
        + '<p>The orchestrator\'s plan states the limit of this anonymization:</p>' + plan_q
        + '<h3>Phase 2: letters per judge</h3>'
        + quote_sentence(site, jr, "own seeded shuffle")
        + t2 + patch_q + native
    )


def sec_effort(site: Site, srcs: dict[str, Src]) -> str:
    ro, jr = srcs[RO_README], srcs[J_README]
    _, ln, body = ro.section(r"Deviations|incidents")
    items = list_items(body, ln)
    eff = next((it for it in items if (split_lead(it["text"])[0] or "").lower().startswith("effort")), None)
    if eff is None:
        raise DataError(f"{RO_README}: no 'Effort' item in the deviations section")
    asked = ""
    p = srcs.get(f"{RO}/PROMPT.md")
    if p:
        try:
            asked = quote_sentence(site, p, "xhigh", label=f"{p.path} (the user's request), line {p.line_of('xhigh')}")
        except DataError:
            asked = ""
    tr = ""
    tpath = f"{RO}/TRANSCRIPT.md"
    if os.path.isfile(os.path.join(site.repo, tpath)):
        t = Src(site, tpath)
        for i, l in enumerate(t.lines, 1):
            mm = re.search(r'"output_config":\s*\{"effort":\s*"[a-z]+"\}', l)
            if mm:
                tr = (f'<p class="small">A logged API request in the orchestrator session log shows <code>{esc(mm.group(0))}</code> '
                      f'(<a href="{esc(site.gh(tpath, i))}" rel="noopener">{esc(tpath)}, line {i} on GitHub</a>; '
                      f'<a href="{esc(site.local(tpath))}">rendered log</a>).</p>')
                break
    return ('<p class="plain-line"><strong>In one line:</strong> the phase-1 review agents were requested at effort “xhigh” but ran at “high”; the phase-2 judges were then run at “high”, the effort the phase-1 agents had actually used.</p>'
            + asked
            + quote(site, ro, eff["text"], eff["line"], block=True, label=f"ReviewOrchestrator/README.md §3.{eff['num']}")
            + tr
            + '<p>Phase 2 was run at the effort the phase-1 agents had actually used:</p>'
            + quote_sentence(site, jr, "the same effort the phase-1 reviewers actually ran at"))


def _ports(site: Site, path: str) -> list[tuple[str | None, str]]:
    """(letter or None, port) for every localhost URL in a prompt file."""
    out = []
    with open(os.path.join(site.repo, path), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\s*([A-Z]):\s*https?://localhost:(\d+)/", line)
            if m:
                out.append((m.group(1), m.group(2)))
    if not out:
        with open(os.path.join(site.repo, path), encoding="utf-8") as f:
            ports = sorted(set(re.findall(r"localhost:(\d+)", f.read())))
        out = [(None, p) for p in ports]
    return out


def sec_serving(site: Site, srcs: dict[str, Src]) -> str:
    m = site.model
    ro, jr = srcs[RO_README], srcs[J_README]
    _, ln, body = ro.section(r"^\d+\.\s*Steps")
    steps = list_items(body, ln)
    serve_step = next((s for s in steps if "http.server" in s["text"]), None)
    out = []
    if serve_step:
        out.append(quote(site, ro, serve_step["text"], serve_step["line"], block=True,
                         label=f"ReviewOrchestrator/README.md §2, step {serve_step['num']}"))
    out.append(quote_sentence(site, ro, "every candidate had its own port"))

    # phase-1 browser reviews: port from each PROMPT.txt
    btypes = [t for t in m.review_types if "browser" in t[0].split("_")]
    rows = []
    unblind = {s: nn for nn, s in m.blind.items()}
    for tid, _, tlabel in btypes:
        for c in sorted(m.candidates, key=lambda c: (unblind.get(c.slug) is None, unblind.get(c.slug, ""), c.index)):
            r = m.review(tid, c.slug)
            if not r or "PROMPT.txt" not in r.files:
                continue
            ports = ", ".join(p for _, p in _ports(site, r.files["PROMPT.txt"])) or "–"
            rows.append(f'<tr><td>{esc(tlabel)} review</td><td><code>{esc(r.blind_id or unblind.get(c.slug, ""))}</code></td><td>{clink(c)}</td>'
                        f'<td class="num">{esc(ports)}</td><td>{site.evidence(r.files["PROMPT.txt"], "PROMPT.txt")}</td></tr>')
    for d in m.discarded:
        if "PROMPT.txt" in d["files"]:
            ports = ", ".join(p for _, p in _ports(site, d["files"]["PROMPT.txt"])) or "–"
            rows.append(f'<tr class="discarded-row"><td>Discarded run <code>{esc(d["id"])}</code></td><td colspan="2"><a href="#discarded">see Discarded run</a></td>'
                        f'<td class="num">{esc(ports)}</td><td>{site.evidence(d["files"]["PROMPT.txt"], "PROMPT.txt")}</td></tr>')
    if rows:
        out.append('<h3>Phase-1 browser reviews</h3><div class="table-wrap"><table class="meth-table"><caption>Port named in each '
                   'browser review prompt (the URL the agent was told to visit).</caption><thead><tr><th scope="col">Run</th>'
                   '<th scope="col">Blind id</th><th scope="col">Candidate</th><th scope="col" class="num">Port</th><th scope="col">Source</th></tr></thead>'
                   f'<tbody>{"".join(rows)}</tbody></table></div>')

    # server logs
    ldir = os.path.join(site.repo, LOGS)
    lrows = []
    for n in sorted(os.listdir(ldir)) if os.path.isdir(ldir) else []:
        if not n.endswith(".log"):
            continue
        p = f"{LOGS}/{n}"
        with open(os.path.join(site.repo, p), encoding="utf-8") as f:
            text = f.read()
        codes = Counter(re.findall(r'"\s(\d{3})\s', text))
        reqs = sum(codes.values())
        mm = re.match(r"http-(\d+)", n)
        nn = f"candidate-{mm.group(1)}" if mm else None
        who = clink(m.cand(m.blind[nn])) if nn in m.blind else '<span class="muted">–</span>'
        cs = ", ".join(f"{k} ×{v}" for k, v in sorted(codes.items()))
        lrows.append(f'<tr><td>{site.evidence(p, n)}</td><td><code>{esc(nn or "–")}</code></td><td>{who}</td>'
                     f'<td class="num">{reqs}</td><td>{esc(cs) or "–"}</td></tr>')
    if lrows:
        out.append('<h3>Server logs</h3><p>One access log per served browser review, counted at build time. '
                   'A <code>304</code> means the browser revalidated a page it already had cached.</p>'
                   '<div class="table-wrap"><table class="meth-table"><caption>Requests per log, from '
                   f'{site.evidence(LOGS, "server-logs/")}; the blind id comes from the file name.</caption><thead><tr><th scope="col">Log</th>'
                   '<th scope="col">Blind id</th><th scope="col">Candidate</th><th scope="col" class="num">Requests</th><th scope="col">Status codes</th></tr></thead>'
                   f'<tbody>{"".join(lrows)}</tbody></table></div>')
        out.append(quote_sentence(site, ro, "304 responses"))

    # phase-2
    out.append("<h3>Phase-2 browser judges</h3>")
    try:
        _, mln, mbody = jr.section(r"^Method$")
        for it in list_items(mbody, mln):
            t, _ = split_lead(it["text"])
            if t and t.lower().startswith(("serving", "scheduling")):
                out.append(quote(site, jr, it["text"], it["line"], block=True))
    except DataError:
        pass
    bj = [j for j in m.judges if j.browser and "PROMPT.txt" in j.files]
    if bj:
        head = "".join(f'<th scope="col" class="num">{esc(j.label)}</th>' for j in bj)
        trs = []
        ports = {j.id: {l: p for l, p in _ports(site, j.files["PROMPT.txt"]) if l} for j in bj}
        for c in m.candidates:
            cells = []
            for j in bj:
                letter = next((l for l, s in j.mapping.items() if s == c.slug), None)
                p = ports[j.id].get(letter) if letter else None
                cells.append(f'<td class="num">{esc(p) + " <span class=muted>(" + esc(letter) + ")</span>" if p else "–"}</td>')
            trs.append(f"<tr><th scope=\"row\">{clink(c)}</th>{''.join(cells)}</tr>")
        srcl = ", ".join(site.evidence(j.files["PROMPT.txt"], f"{j.label} PROMPT.txt") for j in bj)
        out.append('<div class="table-wrap matrix-wrap" role="region" aria-label="Ports per browser judge: candidate × judge">'
                   '<table class="meth-table"><caption>Port (and letter) of each candidate per browser judge, '
                   f'parsed from {srcl}.</caption><thead><tr><th scope="col">Candidate</th>{head}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')
    jlogs = []
    for dp, dn, fn in os.walk(os.path.join(site.repo, "Judge")):
        jlogs += [f for f in fn if f.endswith(".log")]
    if not jlogs:
        out.append('<p class="small muted">The repository holds server logs for the phase-1 browser reviews only; '
                   'no phase-2 server logs are committed, so the judges’ port coverage rests on the README statement above.</p>')
    return "".join(out)


def sec_environment(site: Site, srcs: dict[str, Src]) -> str:
    ro, jr = srcs[RO_README], srcs[J_README]
    _, ln, body = ro.section(r"Deviations|incidents")
    lim = next((it for it in list_items(body, ln) if "limit" in (split_lead(it["text"])[0] or "").lower()), None)
    out = ['<ul class="env-facts">'
           '<li><strong>Device:</strong> desktop Chrome, no XR headset and no WebXR emulator.</li>'
           '<li><strong>Viewport:</strong> the window manager kept the viewport at about 446 px wide and would not resize below it; the phase-2 judges used a 390×844 iframe instead.</li>'
           '<li><strong>Frame rate:</strong> Chrome throttled background windows, so several reviewers could not judge frame rate.</li>'
           '<li><strong>XR entry:</strong> no real VR or AR session was entered.</li></ul>'
           '<p class="small muted">The list above restates the two passages below; the passages are the source.</p>']
    if lim:
        out.append(quote(site, ro, lim["text"], lim["line"], block=True, label=f"ReviewOrchestrator/README.md §3.{lim['num']}"))
    try:
        _, mln, mbody = jr.section(r"^Method$")
        for it in list_items(mbody, mln):
            t, _ = split_lead(it["text"])
            if t and "environment" in t.lower():
                out.append(quote(site, jr, it["text"], it["line"], block=True))
    except DataError:
        pass
    return "".join(out)


def incident_evidence(site: Site, src_path: str, text: str) -> list[str]:
    """Evidence links discovered in an incident's text: repo paths in backticks, blind ids,
    judges and discarded runs it names."""
    m = site.model
    base = os.path.dirname(src_path)
    links, seen = [], set()

    def add(key: str, htmls: str) -> None:
        if key not in seen:
            seen.add(key)
            links.append(htmls)

    index = []
    for top in (RO, "Judge"):
        for dp, dn, fn in os.walk(os.path.join(site.repo, top)):
            dn[:] = sorted(d for d in dn if d != "__pycache__" and not d.startswith("."))
            rel = os.path.relpath(dp, site.repo).replace(os.sep, "/")
            index += [f"{rel}/{d}" for d in dn] + [f"{rel}/{f}" for f in sorted(fn)]
    for tok in re.findall(r"`([^`\n]+)`", text):
        t = tok.strip().rstrip("/")
        if not t or re.search(r"[\s()=:~*<>]", t):
            continue
        hit = None
        for cand in (f"{base}/{t}" if base else t, t):
            if os.path.exists(os.path.join(site.repo, cand)):
                hit = cand
                break
        if not hit:
            matches = [p for p in index if p.endswith("/" + t)]
            hit = matches[0] if len(matches) == 1 else None
        if hit:
            add(hit, site.evidence(hit, hit))
        for d in m.discarded:
            if d["id"].startswith(t) and t != d["id"]:
                add("#discarded", '<a href="#discarded">Discarded run on this page</a>')
    low = text.lower()
    for nn in sorted(set(re.findall(r"candidate-\d+", low))):
        if nn in m.blind:
            c = m.cand(m.blind[nn])
            add(nn, f"<code>{esc(nn)}</code> = {cand_link(c)}")
            for tid, _, tlabel in m.review_types:
                r = m.review(tid, c.slug)
                if r and re.search(rf"\b{re.escape(tlabel.lower())}\b", low) and "REVIEW.md" in r.files:
                    add(r.files["REVIEW.md"], site.evidence(r.files["REVIEW.md"], f"{tlabel} review of {nn}"))
    for j in m.judges:
        if re.search(rf"\b{re.escape(j.label.lower())} judge(?!\w)", low) and "TRANSCRIPT.md" in j.files:
            add(j.files["TRANSCRIPT.md"], site.evidence(j.files["TRANSCRIPT.md"], f"{j.label} judge agent log"))
    return links


def collect_incidents(site: Site, srcs: dict[str, Src]) -> list[dict]:
    out = []
    for path in (RO_README, J_README):
        src = srcs[path]
        found = False
        for i, l in enumerate(src.lines):
            mh = re.match(r"^##\s+(.*?)\s*$", l)
            if not mh or not re.search(r"incident", mh.group(1), re.I):
                continue
            found = True
            heading = mh.group(1)
            _, ln, body = src.section(re.escape(heading) + "$")
            num = re.match(r"^(\d+)\.", heading)
            for it in list_items(body, ln):
                title, rest = split_lead(it["text"])
                if title is None:
                    words = it["text"].split()
                    title, rest = " ".join(words[:6]) + ("…" if len(words) > 6 else ""), it["text"]
                ref = f"§{num.group(1)}.{it['num']}" if num and it["num"] else f"“{heading}”"
                out.append({"src": src, "heading": heading, "title": title, "body": rest, "raw": it["text"],
                            "line": it["line"], "ref": ref, "id": "incident-" + md.slugify(f"{os.path.dirname(path)}-{title}")[:60]})
        if not found:
            raise DataError(f"{path}: no '## …incidents…' section found")
    return out


def sec_incidents(site: Site, srcs: dict[str, Src]) -> tuple[str, int]:
    incs = collect_incidents(site, srcs)
    groups: dict[str, list[dict]] = {}
    for inc in incs:
        groups.setdefault(inc["src"].path, []).append(inc)
    parts = [f'<p>Every item of the incident sections of both READMEs, verbatim and in their original order ({len(incs)} in total). '
             'The heading of each is the item\'s own bold lead; links below each item point to the files it names.</p>']
    ids = set()
    rendered = 0
    nav = []
    for path, items in groups.items():
        parts.append(f'<h3>{esc(path)} · “{esc(items[0]["heading"])}”</h3>')
        for inc in items:
            iid = inc["id"]
            k = 2
            while iid in ids:
                iid = f'{inc["id"]}-{k}'
                k += 1
            ids.add(iid)
            ev = incident_evidence(site, path, inc["raw"])
            ev += [f'<a href="#{k}">{esc(lab)} section on this page</a>' for k, lab in TOC
                   if k not in ("incidents", "caveats") and re.search(rf"\b{k}", inc["title"].lower())]
            ev_html = ("<ul class=\"inc-ev\">" + "".join(f"<li>{e}</li>" for e in ev) + "</ul>") if ev else ""
            title_html = md.render_inline(inc["title"])
            nav.append(f'<li><a href="#{iid}">{title_html}</a></li>')
            parts.append(
                f'<article class="incident" id="{iid}"><h4><span class="inc-ref">{esc(inc["ref"])}</span> {title_html}</h4>'
                f'<blockquote class="quote">{render_md(site, path, text=inc["body"], heading_ids=False)}'
                f'<cite>{inc["src"].ev(f"{path}, line {inc["line"]}", inc["line"])}</cite></blockquote>'
                + (f'<div class="small inc-ev-wrap"><span class="muted">Evidence:</span>{ev_html}</div>' if ev_html else "")
                + "</article>")
            rendered += 1
    assert rendered == len(incs), f"methodology: rendered {rendered} incidents, parsed {len(incs)}"
    text = " ".join(i["raw"] for i in incs).lower()
    for must in ("redact", "c02", "alert(", "privacy"):
        assert must in text, f"methodology: no incident mentions {must!r}; check the README incident sections"
    jump = f'<nav class="inc-nav" aria-label="Incidents"><ol>{"".join(nav)}</ol></nav>'
    return parts[0] + jump + "".join(parts[1:]), rendered


def sec_discarded(site: Site, srcs: dict[str, Src]) -> str:
    m = site.model
    ro = srcs[RO_README]
    if not m.discarded:
        return '<p>No discarded runs are recorded.</p>'
    out = []
    for d in m.discarded:
        out.append(f'<h3 id="discarded-{esc(d["id"])}"><code>{esc(d["id"])}</code></h3>')
        try:
            out.append("<p>Why it was discarded, from the orchestrator README:</p>" + quote_sentence(site, ro, "cached page")
                       if "cached" in d["id"] else "")
        except DataError:
            pass
        try:
            out.append(quote_sentence(site, ro, d["id"]))
        except DataError:
            pass
        rp = d["files"].get("REVIEW.md")
        if rp and d["md"]:
            rsrc = Src(site, rp)
            try:
                _, line = parse_overall(d["md"], rp)
                n = rsrc.line_of(line)
                out.append("<p>The discarded review's own verdict, verbatim (it describes the cached page, not the candidate it was meant to test):</p>")
                out.append(quote(site, rsrc, line.lstrip("# ").strip(), n))
            except DataError:
                pass
            v = section(d["md"], "Verdict")
            if v:
                n = rsrc.line_of("## Verdict") + 1
                while n <= len(rsrc.lines) and not rsrc.lines[n - 1].strip():
                    n += 1
                out.append(quote(site, rsrc, v, n, block=True))
        files = " · ".join(site.evidence(p, n) for n, p in sorted(d["files"].items()))
        out.append(f'<p class="small">Files: {files} · folder {site.evidence(d["dir"], d["dir"] + "/")}</p>')
        if d["shots"]:
            figs = []
            for s in d["shots"]:
                name = os.path.splitext(os.path.basename(s.path))[0]
                words = re.sub(r"^\d+-", "", name).replace("-", " ").replace("_", " ")
                alt = f"Screenshot from the discarded run {d['id']}: {words}"
                src = "@/" + site.media(s.path)
                figs.append(f'<figure class="shot"><a href="{src}"><img src="{src}" width="{s.width}" height="{s.height}" alt="{esc(alt)}" loading="lazy" decoding="async"></a>'
                            f'<figcaption><span class="cap-src">Discarded run · <code>{esc(os.path.basename(s.path))}</code></span></figcaption></figure>')
            out.append(f'<div class="gallery">{"".join(figs)}</div>')
    return "".join(out)


def prompt_files(site: Site) -> list[tuple[str, str]]:
    """[(version 'v0', 'prompt0.txt')] for every promptN.txt at the repo root, by N."""
    found = []
    for n in os.listdir(site.repo):
        mm = re.fullmatch(r"prompt(\d+)\.txt", n)
        if mm:
            found.append((int(mm.group(1)), n))
    return [(f"v{k}", n) for k, n in sorted(found)]


def word_diff(a: str, b: str) -> tuple[str, list[tuple[str, str]]]:
    ta, tb = re.findall(r"\s+|\S+", a), re.findall(r"\s+|\S+", b)
    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
    out, changes = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        old, new = "".join(ta[i1:i2]), "".join(tb[j1:j2])
        if op == "equal":
            out.append(esc(new))
            continue
        # whitespace at the edges of a change stays outside the marks (from the new text when there is one)
        ref = new if new.strip() else old
        lead = ref[:len(ref) - len(ref.lstrip())]
        trail = ref[len(ref.rstrip()):]
        out.append(esc(lead))
        if old.strip():
            out.append(f'<del><span class="sr-only">[removed: </span>{esc(old.strip())}<span class="sr-only">]</span></del>')
        if old.strip() and new.strip():
            out.append(" ")
        if new.strip():
            out.append(f'<ins><span class="sr-only">[added: </span>{esc(new.strip())}<span class="sr-only">]</span></ins>')
        out.append(esc(trail))
        if old.strip() or new.strip():
            changes.append((old.strip(), new.strip()))
    return "".join(out), changes


def sec_prompts(site: Site, srcs: dict[str, Src]) -> str:
    m = site.model
    pf = prompt_files(site)
    texts = {}
    cols = []
    for v, n in pf:
        with open(os.path.join(site.repo, n), encoding="utf-8") as f:
            texts[v] = f.read()
        users = [c for c in m.candidates if c.prompt == v]
        ul = ", ".join(cand_link(c) for c in users) or '<span class="muted">none</span>'
        cols.append(f'<div class="prompt-col"><h3>{prompt_badge(v)} Prompt {esc(v)} <span class="muted small">· {site.evidence(n, n)}</span></h3>'
                    f'<pre class="prompt-text" tabindex="0" aria-label="{esc(n)}, verbatim">{esc(texts[v])}</pre>'
                    f'<p class="small">Used by: {ul}</p></div>')
    ro = srcs[RO_README]
    pl = ro.line_of("Both are verbatim from the chats")
    out = ['<p>Both task prompts, verbatim. The README notes:</p>' + quote(site, ro, ro.lines[pl - 1].strip(), pl),
           f'<div class="prompt-pair">{"".join(cols)}</div>']
    for (va, _), (vb, _) in zip(pf, pf[1:]):
        dhtml, changes = word_diff(texts[va], texts[vb])
        lis = []
        for old, new in changes:
            if old and new:
                lis.append(f"<li>Replaced <q>{esc(old)}</q> with <q>{esc(new)}</q></li>")
            elif new:
                lis.append(f"<li>Added <q>{esc(new)}</q></li>")
            else:
                lis.append(f"<li>Removed <q>{esc(old)}</q></li>")
        out.append(f'<h3>What {esc(vb)} changed relative to {esc(va)}</h3>'
                   '<p class="small muted diff-key">Word-level diff computed at build time. Key: '
                   '<del class="key">removed</del> (struck through, “−”) is only in ' + esc(va) + '; '
                   '<ins class="key">added</ins> (underlined, “+”) is only in ' + esc(vb) + '.</p>'
                   f'<div class="diff" tabindex="0" aria-label="Word diff {esc(va)} to {esc(vb)}">{dhtml}</div>'
                   f'<p class="small">The same changes as a list ({len(changes)}):</p><ul class="small diff-list">{"".join(lis)}</ul>')
    # orchestrator prompts and log
    ol = []
    for p, label in ((f"{RO}/PROMPT.md", "the user's original request to the orchestrator"),
                     (f"{RO}/PROMPTS.md", "every message the user typed in the orchestrator session"),
                     (f"{RO}/PLAN.md", "the approved plan"),
                     (f"{RO}/TRANSCRIPT.md", "the orchestrator's full session log")):
        if os.path.isfile(os.path.join(site.repo, p)):
            ol.append(f"<li>{site.evidence(p, os.path.basename(p))}: {esc(label)}</li>")
    out.append(f'<h3>Orchestrator prompts and log</h3><ul>{"".join(ol)}</ul>')
    # every agent prompt
    rt = m.review_types
    head = "".join(f'<th scope="col">{esc(l)} review</th>' for _, _, l in rt)
    trs = []
    for c in m.candidates:
        cells = []
        for tid, _, _ in rt:
            r = m.review(tid, c.slug)
            cells.append(f'<td>{site.evidence(r.files["PROMPT.txt"], "PROMPT.txt")}</td>' if r and "PROMPT.txt" in r.files else "<td>–</td>")
        trs.append(f"<tr><th scope=\"row\">{clink(c)}</th>{''.join(cells)}</tr>")
    out.append('<h3>Every agent prompt</h3><p>Each reviewer and judge prompt was saved before its agent launched. Review prompts:</p>'
               '<div class="table-wrap matrix-wrap" role="region" aria-label="Reviewer prompts: candidate × review type">'
               '<table class="meth-table"><caption>Phase-1 reviewer prompts, one per candidate and review type.</caption>'
               f'<thead><tr><th scope="col">Candidate</th>{head}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')
    jl = "".join(f'<li>{esc(j.label)} judge: {site.evidence(j.files["PROMPT.txt"], j.files["PROMPT.txt"])}</li>'
                 for j in m.judges if "PROMPT.txt" in j.files)
    if jl:
        out.append(f'<p>Judge prompts:</p><ul class="small">{jl}</ul>')
    return "".join(out)


def sec_derived(site: Site) -> str:
    m = site.model
    tag = '<span class="derived">derived</span>'
    ex = ""
    order = [c for c in m.ordered() if m.ranks(c.slug)]
    if order:
        c = order[0]
        r = m.ranks(c.slug)
        vals = [r[j.id] for j in m.judges if j.id in r]
        lo, hi, sd = m.spread(c.slug)
        ex = (f'<p class="small">Worked example for {cand_link(c)}: ranks {", ".join(str(v) for v in vals)} → '
              f'mean = {sum(vals)} / {len(vals)} = {fmt_mean(m.mean_rank(c.slug))}; spread {lo}–{hi}; σ = {sd:.2f}.</p>')
    kx = ""
    pairs = m.kendall_pairs()
    if pairs:
        a, b, tau, n = pairs[0]
        kx = (f'<p class="small">Example: {esc(a.label)} vs {esc(b.label)} over {n} common candidates, τ<sub>b</sub> = '
              f'{"–" if tau is None else f"{tau:.2f}"}.</p>')
    return (
        '<p>The judges produced ranks only. Everything below is computed by this site from those ranks; none of these numbers comes from a judge or reviewer.</p>'
        '<dl class="formulas">'
        f'<dt>Mean rank {tag}</dt><dd><p class="formula">mean = (r<sub>1</sub> + … + r<sub>n</sub>) / n</p>'
        '<p>over the n judges that ranked the candidate (a judge that did not rank it is left out). Shown to one decimal. '
        'Equal means are shown as ties; the place is a competition rank (1, 1, 3, …).</p>' + ex + '</dd>'
        f'<dt>Spread and σ {tag}</dt><dd><p class="formula">spread = min(r) to max(r) &nbsp;·&nbsp; σ = √( Σ (r<sub>i</sub> − mean)² / n )</p>'
        '<p>σ is the population standard deviation of the candidate\'s ranks: 0 means every judge agreed; larger values mean the judges disagreed more.</p></dd>'
        f'<dt>Kendall τ<sub>b</sub> {tag}</dt><dd><p class="formula">τ<sub>b</sub> = (C − D) / √( (C + D + T<sub>a</sub>) · (C + D + T<sub>b</sub>) )</p>'
        '<p>for two judges, over every pair of candidates both ranked: C = pairs ordered the same way, D = pairs ordered oppositely, '
        'T<sub>a</sub>/T<sub>b</sub> = pairs tied in only one judge\'s ranking. +1 = identical order, 0 = unrelated, −1 = reversed.</p>' + kx + '</dd>'
        '</dl>'
        '<p>The tables and charts are on <a href="@/rankings/">Rankings</a>; the mean column reproduces the table in '
        f'{site.evidence(J_README, "Judge/README.md")}. Phase-1 overall scores are the reviewers\' own numbers, taken as the first number on each review\'s overall-score line.</p>')


def sec_reproduce(site: Site, srcs: dict[str, Src]) -> str:
    ro = srcs[RO_README]
    head, ln, body = ro.section(r"Reproduc")
    stage_of = {t: label for _, label, tools in STAGES for t in tools}
    tdir = os.path.join(site.repo, TOOLS)
    rows = []
    for t in sorted(os.listdir(tdir)) if os.path.isdir(tdir) else []:
        if t.endswith(".py"):
            p = f"{TOOLS}/{t}"
            rows.append(f'<tr><th scope="row">{site.evidence(p, t)}</th><td>{esc(stage_of.get(t, "–"))}</td><td>{esc(docstring(site, p))}</td></tr>')
    return (f'<p>From {ro.ev(f"ReviewOrchestrator/README.md “{head}”", ln - 1)}, verbatim:</p>'
            f'<blockquote class="quote">{render_md(site, RO_README, text=body, heading_ids=False)}<cite>{ro.ev(f"{RO_README}, line {ln - 1}", ln - 1)}</cite></blockquote>'
            f'<p>All tools: {site.evidence(TOOLS, TOOLS + "/")}. The first line of each docstring, verbatim:</p>'
            '<div class="table-wrap"><table class="meth-table"><thead><tr><th scope="col">Tool</th><th scope="col">Stage</th>'
            f'<th scope="col">Docstring</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            '<p class="small">The site itself is built from the committed files by <code>site/build.py</code>; see '
            f'{site.evidence("site/README.md", "site/README.md")}.</p>')


# ---------------------------------------------------------------- build

def build(site: Site) -> None:
    srcs = {p: Src(site, p) for p in (RO_README, J_README)}
    for p in (f"{RO}/PLAN.md", f"{RO}/PROMPT.md"):
        if os.path.isfile(os.path.join(site.repo, p)):
            srcs[p] = Src(site, p)

    incidents_html, n_inc = sec_incidents(site, srcs)
    sections = {
        "caveats": sec_caveats(site, srcs),
        "pipeline": sec_pipeline(site, srcs),
        "blinding": sec_blinding(site, srcs),
        "effort": sec_effort(site, srcs),
        "serving": sec_serving(site, srcs),
        "environment": sec_environment(site, srcs),
        "incidents": incidents_html,
        "discarded": sec_discarded(site, srcs),
        "prompts": sec_prompts(site, srcs),
        "derived": sec_derived(site),
        "reproduce": sec_reproduce(site, srcs),
    }
    labels = dict(TOC)
    labels["incidents"] = f"Incidents ({n_inc})"
    toc = "".join(f'<li><a href="#{k}">{esc(labels[k])}</a></li>' for k, _ in TOC)
    body = [
        '<header class="meth-head"><h1>Methodology</h1>'
        '<p class="lede">How the eight products were collected, blinded, reviewed, judged and aggregated, '
        'what went wrong along the way, and what the numbers on this site can and cannot tell you. '
        'Wherever possible this page quotes the process record instead of summarising it.</p></header>',
        f'<nav class="meth-toc" aria-label="On this page"><h2 class="toc-h">On this page</h2><ol>{toc}</ol></nav>',
    ]
    for k, _ in TOC:
        body.append(f'<section class="meth-sec" aria-labelledby="{k}"><h2 id="{k}">{esc(labels[k])}</h2>{sections[k]}'
                    '<p class="to-top"><a href="#main">Back to top</a></p></section>')
    html_body = "\n".join(body)
    site.page("methodology/index.html", "Methodology", html_body, section="methodology",
              crumbs=[("Methodology", "methodology/")],
              description="How the MandelbrotXR experiment was run: caveats, pipeline, blinding, effort, serving, environment limits, every incident, both prompts verbatim.")
    site.search_doc("methodology/", "Methodology", "page", "Methodology",
                    plain(html_body.replace("Back to top", "")))
