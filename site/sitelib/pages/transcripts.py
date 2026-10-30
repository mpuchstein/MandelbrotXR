"""Transcripts: rendered chat transcripts and agent logs (brief §7).

transcripts/                 index of every transcript, grouped by kind
transcripts/<tid>/           page 1: intro (the file's header, verbatim), full message index, first messages
transcripts/<tid>/<n>/       later pages (split by rendered size so each page stays phone-sized)

Every message gets id="m-<n>" (numbered across the whole transcript) and a visible "#n" permalink.
Thinking and tool input/output are collapsed into <details class="fold">, including Copilot-style
"**Thinking**" paragraphs (see thinking_split). Bodies go through md.render,
so literal <script>, <system-reminder> etc. in the corpus are shown as text.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .. import md
from ..fragments import cand_url, judge_url, md_link, render_md, review_url
from ..layout import Site, TranscriptSource, esc

ORDER = 700

PAGE_BUDGET = 280_000     # bytes of HTML per page (messages + indexes); one oversized message gets its own page
SEARCH_CAP = 4_000        # indexed characters per message
PEEK = 96                 # characters of a fold's one-line preview

KINDS = [  # kind -> (heading, explanation)
    ("chat", "Chat transcripts", "The conversation with each assistant that produced a candidate, extracted from the vendor's web UI or session log."),
    ("review", "Phase-1 review agent logs", "One blind reviewer agent per review type and candidate."),
    ("judge", "Phase-2 judge agent logs", "One blind judge agent per judge type, ranking all candidates."),
    ("orchestrator", "Orchestrator", "The main session that extracted, blinded and ran every review and judge."),
    ("blind", "Anonymized transcripts", "The redacted chat transcripts exactly as the transcript reviewers and judges saw them."),
    ("discarded", "Discarded runs", "Runs that were thrown away and redone; kept for the record."),
]
CHIP = {"chat": "Chat", "review": "Review logs", "judge": "Judge logs", "orchestrator": "Orchestrator",
        "blind": "Anonymized", "discarded": "Discarded"}  # short jump-link labels (fall back to the heading)
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

_ROLE = r"(?:User|Assistant|Tool|System)\b"
_FIRST_HEAD = re.compile(r"(#{1,6})[ \t]+" + _ROLE)
_FENCE_OPEN = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")
_FENCE_CLOSE = re.compile(r" {0,3}(`{3,}|~{3,})[ \t]*$")
_DETAILS_OPEN = re.compile(r"<details(?:\s+open)?\s*>\s*(?:<summary>(.*)</summary>)?\s*$", re.I)
_DETAILS_CLOSE = re.compile(r"</details>\s*$", re.I)
_SUMMARY = re.compile(r"\s*<summary>(.*)</summary>\s*$", re.I)
_TOOL_CALL = re.compile(r"\*\*Tool call `([^`]+)`\*\*(?::\s*(.*))?\s*$")
_HEADING_TAG = re.compile(r"<(/?)h([1-6])([\s>])")
_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}[T ][\d:.]+Z?")
_TS_PARTS = re.compile(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})")
_MSG_TS = re.compile(r"\(message \d+, (" + _TIMESTAMP.pattern + r")\)")
_HR = re.compile(r" {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")


# ---------------------------------------------------------------- parsing

class _Fences:
    """Tracks fenced code blocks line by line, with the same open/close rules as md.py."""

    def __init__(self) -> None:
        self.marker: str | None = None

    def feed(self, line: str) -> bool:
        """Feed one line; return True if the line is (part of) a fenced block, fence lines included."""
        if self.marker:
            m = _FENCE_CLOSE.match(line)
            if m and m.group(1)[0] == self.marker[0] and len(m.group(1)) >= len(self.marker):
                self.marker = None
            return True
        m = _FENCE_OPEN.match(line)
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            self.marker = m.group(1)
            return True
        return False


@dataclass
class Msg:
    n: int
    heading: str          # heading text as written, without the #s
    role: str             # User / Assistant / Tool output / System ...
    meta: str             # rest of the heading (timestamp, message number, label)
    body: str             # Markdown body
    line: int             # 1-based line of the heading in the source file
    html: str = ""
    page: int = 1
    first: str = ""       # first words, for the indexes


@dataclass
class Transcript:
    src: TranscriptSource
    header: str
    msgs: list[Msg]
    lines: int
    pages: list[list[Msg]] = field(default_factory=list)


def _trim(lines: list[str]) -> list[str]:
    """Strip blank lines and the trailing '---' separator the chat transcripts put between messages."""
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and _HR.match(lines[-1]) and lines[-1].strip().startswith("-"):
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()
    while lines and not lines[0].strip():
        lines.pop(0)
    return lines


def _split_heading(text: str) -> tuple[str, str]:
    m = re.match(r"(Tool output|Tool result|Tool|User|Assistant|System)\b(.*)", text)
    if not m:
        return text, ""
    role, rest = m.group(1), m.group(2).strip()
    rest = rest.lstrip("·").strip()
    if rest.startswith(":"):
        rest = rest[1:].strip()
    return role, rest


def parse(text: str) -> tuple[str, list[Msg], int]:
    """Split a transcript into (header Markdown, messages, line count).
    The message heading level is the level of the first heading (outside code fences) that starts
    with User/Assistant/Tool/System; every heading of exactly that level that starts with one of
    those words begins a new message. Everything before the first message is the header."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    fences, level, starts = _Fences(), None, []
    for i, line in enumerate(lines):
        if fences.feed(line):
            continue
        if level is None:
            m = _FIRST_HEAD.match(line)
            if m:
                level = len(m.group(1))
                head = re.compile("#" * level + r"[ \t]+(" + _ROLE + r".*)")
        if level is not None:
            m = head.match(line)
            if m:
                starts.append((i, m.group(1).strip().rstrip("#").strip()))
    if not starts:
        return "\n".join(_trim(lines)), [], len(lines)
    header = "\n".join(_trim(lines[:starts[0][0]]))
    msgs = []
    for k, (i, heading) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        role, meta = _split_heading(heading)
        msgs.append(Msg(k + 1, heading, role, meta, "\n".join(_trim(lines[i + 1:end])), i + 1))
    return header, msgs, len(lines)


def segments(body: str) -> list[tuple]:
    """Top-level blocks of a message body: ('md', text), ('call', name, desc, fence_text),
    ('details', summary, inner_text). Fence- and nesting-aware."""
    lines = body.split("\n")
    out: list[tuple] = []
    buf: list[str] = []

    def flush():
        if buf and any(l.strip() for l in buf):
            out.append(("md", "\n".join(buf)))
        buf.clear()

    fences = _Fences()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if fences.feed(line):
            buf.append(line)
            i += 1
            continue
        m = _DETAILS_OPEN.match(line)
        if m:
            summary, j = m.group(1), i + 1
            if summary is None and j < n and _SUMMARY.match(lines[j]):
                summary, j = _SUMMARY.match(lines[j]).group(1), j + 1
            depth, inner, f2 = 1, [], _Fences()
            while j < n:
                l2 = lines[j]
                if not f2.feed(l2):
                    if _DETAILS_OPEN.match(l2) or l2.strip().lower() == "<details>":
                        depth += 1
                    elif _DETAILS_CLOSE.match(l2):
                        depth -= 1
                        if depth == 0:
                            break
                inner.append(l2)
                j += 1
            flush()
            out.append(("details", summary or "Details", "\n".join(inner)))
            i = j + 1
            continue
        m = _TOOL_CALL.match(line)
        if m:
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and _FENCE_OPEN.match(lines[j]):
                f2, k = _Fences(), j
                while k < n:
                    f2.feed(lines[k])
                    k += 1
                    if f2.marker is None:
                        break
                flush()
                out.append(("call", m.group(1), (m.group(2) or "").strip(), "\n".join(lines[j:k])))
                i = k
                continue
        buf.append(line)
        i += 1
    flush()
    return out


# ---------------------------------------------------------------- rendering

def _size(text: str) -> str:
    lines = text.count("\n") + 1 if text else 0
    b = len(text.encode("utf-8"))
    kb = f"{b} B" if b < 1000 else f"{b / 1000:.1f} kB"
    return f"{lines} line{'s' if lines != 1 else ''} · {kb}"


def _clip(s: str, n: int = PEEK) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _fence_inner(fence: str) -> str:
    ls = fence.split("\n")
    if len(ls) >= 2 and _FENCE_CLOSE.match(ls[-1]):
        ls = ls[1:-1]
    else:
        ls = ls[1:]
    return "\n".join(ls)


def _call_desc(name: str, inner: str) -> str:
    """One line describing a tool call: its description, else the first line of its main argument."""
    keys = ("description", "command", "file_path", "path", "pattern", "url", "query", "prompt", "skill", "subagent_type")
    vals: dict[str, str] = {}
    try:
        d = json.loads(inner)
        if isinstance(d, dict):
            vals = {k: v for k, v in d.items() if isinstance(v, str)}
    except ValueError:
        for k in keys:
            m = re.search(r'"' + k + r'"\s*:\s*"((?:[^"\\]|\\.)*)', inner)
            if m:
                try:
                    vals[k] = json.loads('"' + m.group(1) + '"')
                except ValueError:
                    vals[k] = m.group(1)
    for k in keys:
        v = vals.get(k, "").strip()
        if v:
            return v.split("\n", 1)[0]
    first = next((l.strip() for l in inner.split("\n") if l.strip() not in ("", "{", "}", "[", "]")), "")
    return first


def tool_chip(name: str) -> str:
    """The tool-name chip of a fold summary. A long MCP name ('mcp__server__tool') shows its last segment;
    the full name is in the title and in the accessible text, so nothing is lost."""
    parts = name.split("__")
    if name.startswith("mcp__") and len(parts) >= 3:
        return (f'<code class="fold-tool" title="{esc(name)}"><span class="sr-only">{esc("__".join(parts[:-1]))}__</span>'
                f'{esc(parts[-1])}</code>')
    return f'<code class="fold-tool" title="{esc(name)}">{esc(name)}</code>'


def _demote(html_: str, by: int) -> str:
    return _HEADING_TAG.sub(lambda m: f"<{m.group(1)}h{min(6, int(m.group(2)) + by)}{m.group(3)}", html_)


_THINKING = "**Thinking**"


def _blocks(text: str) -> list[str]:
    """Blank-line separated blocks of Markdown (fence-aware: a fenced block stays whole)."""
    out: list[str] = []
    cur: list[str] = []
    fences = _Fences()
    for line in text.split("\n"):
        if not fences.feed(line) and not line.strip():
            if cur:
                out.append("\n".join(cur))
                cur = []
            continue
        cur.append(line)
    if cur:
        out.append("\n".join(cur))
    return out


def thinking_split(text: str, last: bool) -> list[tuple[str, str]]:
    """Copilot-style 'Thinking' sections in one Markdown segment: a paragraph that is only **Thinking** starts a
    block that runs up to the next **Thinking** paragraph, the next blockquote (the '> …' tool summary line) or the
    end of the message. Returns [('md', text) | ('thinking', text)]. Not folded: a block that runs to the end of the
    message (the final answer, which follows the last tool summary) and an empty block (label directly followed
    by a tool summary); their label paragraph stays as written. `last`: this segment ends the message."""
    blocks = _blocks(text)
    if not any(b.strip() == _THINKING for b in blocks):
        return [("md", text)]
    out: list[tuple[str, str]] = []
    plain: list[str] = []
    i, n = 0, len(blocks)
    while i < n:
        if blocks[i].strip() != _THINKING:
            plain.append(blocks[i])
            i += 1
            continue
        j = i + 1
        while j < n and blocks[j].strip() != _THINKING and not blocks[j].lstrip().startswith(">"):
            j += 1
        inner = blocks[i + 1:j]
        if not inner or (j == n and last):
            plain.extend(blocks[i:j])
        else:
            if plain:
                out.append(("md", "\n\n".join(plain)))
                plain = []
            out.append(("thinking", "\n\n".join(inner)))
        i = j
    if plain:
        out.append(("md", "\n\n".join(plain)))
    return out


def _thinking_fold(inner: str, link) -> str:
    peek = _clip(md.to_text(inner).split("\n", 1)[0])
    return (f'<details class="fold fold-thinking"><summary><span class="fold-kind">Thinking</span>'
            f'{f" <span class=fold-peek>{esc(peek)}</span>" if peek else ""}'
            f' <span class="fold-size">{esc(_size(inner.strip()))}</span></summary>\n'
            f'{md.render(inner, link=link, heading_ids=False)}</details>')


def render_body(body: str, link) -> str:
    parts = []
    segs = segments(body)
    for k, seg in enumerate(segs):
        if seg[0] == "md":
            for kind, text in thinking_split(seg[1], k == len(segs) - 1):
                parts.append(md.render(text, link=link, heading_ids=False) if kind == "md" else _thinking_fold(text, link))
        elif seg[0] == "call":
            _, name, desc, fence = seg
            inner = _fence_inner(fence)
            peek = desc or _call_desc(name, inner)
            parts.append(
                f'<details class="fold fold-call"><summary><span class="fold-kind">Tool call</span> {tool_chip(name)}'
                f'{f" <span class=fold-peek>{esc(_clip(peek))}</span>" if peek else ""}'
                f' <span class="fold-size">{esc(_size(inner))}</span></summary>\n{md.render(fence, link=link, heading_ids=False)}</details>')
        else:
            _, summary, inner = seg
            plain = re.sub(r"<[^>]*>|`", "", summary).strip()
            kind = "thinking" if plain.lower().startswith("thinking") else "result" if plain.lower().startswith("tool result") else "other"
            text = md.to_text(inner) if kind == "result" else ""
            peek = _clip(text.split("\n", 1)[0]) if text else ""
            parts.append(
                f'<details class="fold fold-{kind}"><summary><span class="fold-kind">{md.render_inline(summary)}</span>'
                f'{f" <span class=fold-peek>{esc(peek)}</span>" if peek else ""}'
                f' <span class="fold-size">{esc(_size(inner.strip()))}</span></summary>\n'
                f'{md.render(inner, link=link, heading_ids=False)}</details>')
    return _demote("\n".join(parts), 3)


def _nb(text: str) -> str:
    """Keep a dash with the word before it (' — ' -> NBSP + '— ') so a wrapped title never starts a line with it."""
    return re.sub(r" ([—–]) ", "\u00a0\\1 ", text)


def fmt_ts(iso: str) -> str:
    """'2026-10-29T14:22:49.128498Z' -> '29 Oct 2026, 14:22 UTC' (deterministic; the ISO value is kept in datetime/title)."""
    m = _TS_PARTS.match(iso)
    if not m:
        return iso
    y, mo, d, hh, mm = m.groups()
    return f"{int(d)} {_MONTHS[int(mo) - 1]} {y}, {hh}:{mm}" + (" UTC" if iso.endswith("Z") else "")


def meta_parts(meta: str) -> list[tuple[str, str]]:
    """The heading's meta split into ('text', s) and ('ts', iso) parts. The '(message N, <time>)' form some
    exports use (a 0-based counter of the exporting tool) is reduced to its time, so the only visible message
    number is the 1-based '#n'; the full heading stays in the time element's title."""
    m = _MSG_TS.fullmatch(meta.strip())
    if m:
        return [("ts", m.group(1))]
    out, pos = [], 0
    for t in _TIMESTAMP.finditer(meta):
        if t.start() > pos:
            out.append(("text", meta[pos:t.start()]))
        out.append(("ts", t.group(0)))
        pos = t.end()
    if pos < len(meta):
        out.append(("text", meta[pos:]))
    return out


def meta_html(meta: str) -> str:
    return "".join(esc(v) if k == "text" else
                   f'<time class="tx-time" datetime="{esc(v)}" title="{esc(meta.strip())}">{esc(fmt_ts(v))}</time>'
                   for k, v in meta_parts(meta))


def meta_text(meta: str) -> str:
    return "".join(v if k == "text" else fmt_ts(v) for k, v in meta_parts(meta)).strip()


def path_html(path: str) -> str:
    """A repo path that breaks only after '/': each segment is kept whole (.nw), with <wbr> after each slash."""
    return "/<wbr>".join(f'<span class="nw">{esc(seg)}</span>' for seg in path.split("/"))


def role_class(role: str) -> str:
    r = role.lower()
    return "user" if r.startswith("user") else "tool" if r.startswith("tool") else "system" if r.startswith("system") else "assistant"


def render_msg(m: Msg, link) -> str:
    body = render_body(m.body, link)
    if "thinking" in m.meta.lower() and body:
        body = (f'<details class="fold fold-thinking"><summary><span class="fold-kind">{esc(m.meta)}</span>'
                f' <span class="fold-size">{esc(_size(m.body))}</span></summary>\n{body}</details>')
    # the meta goes on its own line below the role (CSS); timestamps never break at their hyphens
    meta = f' <span class="msg-meta">{meta_html(m.meta)}</span>' if m.meta else ""
    return (f'<article class="msg msg-{role_class(m.role)}" id="m-{m.n}" data-line="{m.line}">'
            f'<header class="msg-head"><h3 class="msg-title"><span class="msg-role">{esc(m.role)}</span>{meta}</h3>'
            f'<a class="msg-num" href="#m-{m.n}" title="Permalink to message {m.n}">#{m.n}</a></header>'
            f'<div class="msg-body md">{body}</div></article>\n')


def load(site: Site, src: TranscriptSource) -> Transcript:
    with open(f"{site.repo}/{src.path}", encoding="utf-8") as f:
        text = f.read()
    header, msgs, nlines = parse(text)
    link = md_link(site, src.path)
    for m in msgs:
        m.html = render_msg(m, link)
        first = md.to_text(m.body)
        m.first = _clip(first, 64) if first else ""
    return Transcript(src, header, msgs, nlines)


def page_url(t: Transcript, k: int) -> str:
    return f"@/transcripts/{t.src.id}/" + (f"{k}/" if k > 1 else "")


def msg_url(t: Transcript, m: Msg, here: int) -> str:
    return (f"#m-{m.n}" if m.page == here else f"{page_url(t, m.page)}#m-{m.n}")


def paginate(t: Transcript, page1_extra: int) -> None:
    pages: list[list[Msg]] = [[]]
    size = page1_extra
    for m in t.msgs:
        cost = len(m.html) + 180  # + index entry
        if pages[-1] and size + cost > PAGE_BUDGET:
            pages.append([])
            size = 0
        pages[-1].append(m)
        size += cost
    for k, pg in enumerate(pages, 1):
        for m in pg:
            m.page = k
    t.pages = pages


def index_items(t: Transcript, msgs: list[Msg], here: int) -> str:
    return "".join(
        f'<li><a href="{msg_url(t, m, here)}"><span class="ix-n">#{m.n}</span> {esc(m.role)}</a>'
        f'{f" <span class=ix-first>{esc(m.first)}</span>" if m.first else ""}</li>' for m in msgs)


def pager(t: Transcript, here: int, top: bool) -> str:
    if len(t.pages) < 2:
        return ""
    items = []
    for k, pg in enumerate(t.pages, 1):
        rng = f"messages {pg[0].n}–{pg[-1].n}" if pg else "no messages"
        cur = ' aria-current="page"' if k == here else ""
        items.append(f'<li><a href="{page_url(t, k)}" data-page="{k}"{cur} title="Page {k}: {rng}">{k}</a></li>')
    prev = (f'<a class="pg-prev" rel="prev" href="{page_url(t, here - 1)}">← Previous</a>' if here > 1
            else '<span class="pg-prev" aria-hidden="true"></span>')
    nxt = (f'<a class="pg-next" rel="next" href="{page_url(t, here + 1)}">Next →</a>' if here < len(t.pages)
           else '<span class="pg-next" aria-hidden="true"></span>')
    data = ""
    if top:
        ranges = " ".join(f"{pg[0].n}-{pg[-1].n}:{pg[0].line}" for pg in t.pages if pg)
        data = f' data-ranges="{ranges}" data-here="{here}"'
    label = "Transcript pages" if top else "Transcript pages (bottom)"
    return (f'<nav class="pager" aria-label="{label}"{data}>{prev}<ol>{"".join(items)}</ol>{nxt}</nav>')


def tools_bar(t: Transcript) -> str:
    """Controls that need JS: .js-only (visible from first paint when JS runs, absent without it)."""
    if not t.msgs:
        return ""
    jump = ""
    if len(t.pages) > 1 or len(t.msgs) > 20:
        jump = (f'<form class="tx-jump" data-tx-jump><label for="tx-jump-n">Jump to message</label> '
                f'<input id="tx-jump-n" type="number" inputmode="numeric" min="1" max="{len(t.msgs)}" placeholder="1–{len(t.msgs)}" required> '
                f'<button class="btn" type="submit">Go</button></form>')
    return (f'<div class="toolbar tx-tools js-only" data-tx-tools>'
            f'<button class="btn" type="button" data-fold="open">Expand all</button>'
            f'<button class="btn" type="button" data-fold="close">Collapse all</button>{jump}</div>')


def related(site: Site, src: TranscriptSource) -> list[str]:
    m, out = site.model, []
    if src.slug and src.kind in ("chat", "review", "blind"):
        c = m.cand(src.slug)
        out.append(f'<a href="{cand_url(c)}">Candidate: {esc(c.label)}</a>')
    if src.kind == "review":
        r = next((r for r in m.reviews if r.files.get("TRANSCRIPT.md") == src.path), None)
        if r:
            out.append(f'<a href="{review_url(r)}">{esc(r.type_label)} review ({esc(r.blind_id)})</a>')
    if src.kind == "judge":
        j = next((j for j in m.judges if j.files.get("TRANSCRIPT.md") == src.path), None)
        if j:
            out.append(f'<a href="{judge_url(j)}">{esc(j.label)} judge page</a>')
    if src.kind == "blind" and src.slug:
        c = m.cand(src.slug)
        out.append(f'<a href="{site.local(c.transcription)}">Original chat transcript</a>')
    if src.kind == "chat" and src.slug:
        for nn, slug in sorted(m.blind.items()):
            p = f"ReviewOrchestrator/blind/{nn}/TRANSCRIPT.md"
            if slug == src.slug and p in site._tids:
                out.append(f'<a href="{site.local(p)}">Anonymized copy ({esc(nn)})</a>')
    if src.kind in ("discarded", "orchestrator"):
        out.append('<a href="@/methodology/#incidents">Methodology: incidents</a>')
    return out


def build_transcript(site: Site, t: Transcript) -> None:
    src = t.src
    tid = src.id
    link = md_link(site, src.path)
    n_pages = max(1, len(t.pages))
    crumbs_base = [("Transcripts", "transcripts/")]
    ev = site.evidence(src.path, src.path).replace(f">{esc(src.path)}</a>", f">{path_html(src.path)}</a>", 1)
    facts = (f'<ul class="tx-meta"><li>{ev}</li>'
             f'<li class="num">{len(t.msgs):,} message{"s" if len(t.msgs) != 1 else ""} · {t.lines:,} lines'
             f'{f" · {n_pages} pages" if n_pages > 1 else ""}</li>')
    rel = related(site, src)
    if rel:
        facts += "".join(f"<li>{r}</li>" for r in rel)
    facts += "</ul>"
    for k in range(1, n_pages + 1):
        msgs = t.pages[k - 1] if t.pages else []
        parts = []
        title = src.title if k == 1 else f"{src.title} (page {k} of {n_pages})"
        parts.append(f'<h1>{esc(_nb(src.title))}{f" <span class=tx-pageno>page {k} of {n_pages}</span>" if k > 1 else ""}</h1>')
        parts.append(facts)
        if k == 1 and t.header:
            intro = render_md(site, src.path, t.header, id_prefix="intro-")
            parts.append(f'<section class="tx-intro" aria-label="Transcript header (verbatim)">{_demote(intro, 1)}</section>')
        if t.msgs:
            if k == 1:
                parts.append(f'<details class="tx-index"><summary>Message index: all {len(t.msgs)} messages'
                             f'{f" on {n_pages} pages" if n_pages > 1 else ""}</summary><ol class="msg-index">'
                             f'{index_items(t, t.msgs, 1)}</ol></details>')
            else:
                parts.append(f'<details class="tx-index"><summary>On this page: messages {msgs[0].n}–{msgs[-1].n}</summary>'
                             f'<ol class="msg-index">{index_items(t, msgs, k)}</ol>'
                             f'<p class="small"><a href="{page_url(t, 1)}">Full message index on page 1</a></p></details>')
        parts.append(tools_bar(t))
        parts.append(pager(t, k, True))
        if msgs:
            parts.append(f'<h2 class="tx-range">Messages {msgs[0].n}–{msgs[-1].n}'
                         f'{f" <span class=muted>of {len(t.msgs)}</span>" if n_pages > 1 else ""}</h2>')
            parts.append(f'<div class="msgs">{"".join(m.html for m in msgs)}</div>')
        elif not t.msgs:
            parts.append('<p class="muted">No User/Assistant/Tool messages were found in this file; it is shown above as written.</p>')
        parts.append(pager(t, k, False))
        crumbs = crumbs_base + ([(src.title, "")] if k == 1 else [(src.title, page_url(t, 1)[2:]), (f"Page {k}", "")])
        rel_path = f"transcripts/{tid}/index.html" if k == 1 else f"transcripts/{tid}/{k}/index.html"
        site.page(rel_path, title, "\n".join(p for p in parts if p), section="transcripts", crumbs=crumbs,
                  description=f"{src.title}: {len(t.msgs)} messages, rendered from {src.path}.",
                  scripts=["transcripts.js"])
    for m in t.msgs:
        url = f"transcripts/{tid}/" + (f"{m.page}/" if m.page > 1 else "") + f"#m-{m.n}"
        text = md.to_text(m.body)
        if len(text) > SEARCH_CAP:
            text = text[:SEARCH_CAP].rstrip() + " …"
        mt = meta_text(m.meta)
        site.search_doc(url, src.title, "transcript", f"#{m.n} {m.role}" + (f" · {mt}" if mt else ""), text)


def build_index(site: Site, ts: list[Transcript]) -> None:
    m = site.model
    by_kind: dict[str, list[Transcript]] = {}
    for t in ts:
        by_kind.setdefault(t.src.kind, []).append(t)
    total_msgs = sum(len(t.msgs) for t in ts)
    total_lines = sum(t.lines for t in ts)
    parts = ['<h1>Transcripts</h1>',
             f'<p class="lede">Every chat transcript and agent log in the repository, rendered for reading: {len(ts)} files, '
             f'{total_msgs:,} messages, {total_lines:,} lines. Thinking and tool input/output are collapsed; every message has '
             f'an anchor (<code>#m-&lt;n&gt;</code>), and long logs are split into pages.</p>',
             '<p class="note">Transcripts are shown exactly as committed. Where a file\'s header says that tool inputs or '
             'results were cut, or that personal data was redacted, that happened when the transcript was extracted, before '
             'this site was built. Every page links to its file on GitHub at the build commit.</p>',
             '<nav class="tx-kinds" aria-label="Transcript kinds"><ul>' + "".join(
                 f'<li><a class="chip" href="#{k}">{esc(CHIP.get(k, h))} ({len(by_kind[k])})</a></li>'
                 for k, h, _ in KINDS if k in by_kind) + '<li><a class="chip" href="@/source/">All source files</a></li></ul></nav>']

    def stats(t: Transcript) -> str:
        pg = f" · {len(t.pages)} pages" if len(t.pages) > 1 else ""
        return f"{len(t.msgs)} msgs · {t.lines:,} lines{pg}"

    def row(t: Transcript, label: str) -> str:
        return (f'<tr><th scope="row"><a href="{site.local(t.src.path)}">{label}</a></th>'
                f'<td class="num">{len(t.msgs)}</td><td class="num">{t.lines:,}</td><td class="num">{len(t.pages) or 1}</td>'
                f'<td><span class="evidence"><a class="gh" href="{esc(site.gh(t.src.path))}" rel="noopener">GitHub</a></span></td></tr>')

    head = ('<colgroup><col class="c-name"><col class="c-msgs"><col class="c-lines"><col class="c-pages"><col class="c-src"></colgroup>'
            '<thead><tr><th scope="col">Transcript</th><th scope="col" class="num">Messages</th>'
            '<th scope="col" class="num">Lines</th><th scope="col" class="num">Pages</th><th scope="col">Source</th></tr></thead>')
    for kind, heading, expl in KINDS:
        items = by_kind.get(kind)
        if not items:
            continue
        parts.append(f'<section id="{kind}"><h2>{esc(heading)}</h2><p class="sec-lede">{esc(expl)}</p>')
        if kind == "review":
            types = [(tid_, label) for tid_, _, label in m.review_types]
            cell: dict[tuple[str, str], Transcript] = {}
            for t in items:
                r = next((r for r in m.reviews if r.files.get("TRANSCRIPT.md") == t.src.path), None)
                if r:
                    cell[(r.type_id, r.slug)] = t
            slugs = [c.slug for c in m.candidates if any((ty, c.slug) in cell for ty, _ in types)]
            rows = []
            for s in slugs:
                tds = []
                for ty, _ in types:
                    t = cell.get((ty, s))
                    tds.append(f'<td><span class="evidence"><a class="tx-stat" href="{site.local(t.src.path)}">{esc(stats(t))}</a> '
                               f'<a class="gh" href="{esc(site.gh(t.src.path))}" rel="noopener">GitHub</a></span></td>'
                               if t else '<td class="muted">–</td>')
                lab = esc(m.cand(s).label).replace(" · ", "\u00a0·\u00a0")
                rows.append(f'<tr><th scope="row"><a class="tx-cand" href="{cand_url(m.cand(s))}">{lab}</a></th>{"".join(tds)}</tr>')
            parts.append('<div class="table-wrap matrix-wrap scroll-hint tx-wrap" role="region" aria-label="Review agent logs: candidate × review type">'
                         '<table class="tx-matrix"><caption class="sr-only">Review agent logs by candidate (rows) and '
                         'review type (columns)</caption><thead><tr><th scope="col">Candidate</th>'
                         + "".join(f'<th scope="col">{esc(lab)} review</th>' for _, lab in types)
                         + f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
                         '<p class="small muted tx-cap">Rows: candidates; columns: review types. Each cell is one '
                         'review agent log (messages · lines) with its GitHub copy. On narrow screens the table scrolls sideways.</p>')
            rest = [t for t in items if t not in cell.values()]
            if rest:
                parts.append(f'<div class="table-wrap tx-wrap" role="region" aria-label="{esc(heading)}: other logs"><table class="tx-list">{head}<tbody>{"".join(row(t, esc(t.src.title)) for t in rest)}</tbody></table></div>')
        else:
            body = []
            for t in items:
                label = esc(t.src.title)
                if kind == "chat" and t.src.slug:
                    label = esc(m.cand(t.src.slug).label)
                elif kind == "blind":
                    nn = t.src.path.split("/")[2]
                    label = esc(nn) + (f' <span class="muted small">({esc(m.cand(t.src.slug).label)})</span>' if t.src.slug else "")
                elif kind == "judge":
                    label = esc(t.src.title.removesuffix(" judge agent log")) + " judge"
                body.append(row(t, label))
            parts.append(f'<div class="table-wrap tx-wrap" role="region" aria-label="{esc(heading)}"><table class="tx-list">{head}<tbody>{"".join(body)}</tbody></table></div>')
        parts.append('</section>')
    site.page("transcripts/index.html", "Transcripts", "\n".join(parts), section="transcripts", crumbs=[("Transcripts", "")],
              description="Rendered chat transcripts and agent logs of the MandelbrotXR experiment, with an anchor per message.")


def build(site: Site) -> None:
    ts = []
    for src in site.transcript_sources():
        t = load(site, src)
        extra = 4_000 + len(t.header) * 2 + sum(len(m.first) + 120 for m in t.msgs)
        paginate(t, extra)
        ts.append(t)
        build_transcript(site, t)
    build_index(site, ts)
