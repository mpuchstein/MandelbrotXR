"""Safe Markdown to HTML renderer, tuned to the Markdown found in this repository.

Supports a CommonMark/GFM subset: ATX headings, paragraphs, hard breaks, nested
lists, blockquotes, fenced code, GFM tables, thematic breaks and inline markup.
The only raw HTML passed through is block-level ``<details>``/``<summary>``;
every other ``<`` is escaped.
"""
from __future__ import annotations

import html
import re
import string
import unicodedata
from bisect import bisect_left
from html.entities import html5
from typing import Callable, Optional

__all__ = ["render", "render_inline", "slugify", "to_text"]

LinkFn = Optional[Callable[[str], Optional[str]]]

_ASCII_PUNCT = frozenset(string.punctuation)

_ATX = re.compile(r"(#{1,6})(?:[ \t]+|$)(.*)")
_FENCE = re.compile(r"(`{3,}|~{3,})(.*)")
_HR = re.compile(r"([-*_])(?:[ \t]*\1){2,}[ \t]*$")
_ITEM = re.compile(r"(?:[-+*]|(\d{1,9})([.)]))(?=[ \t]|$)")
_DETAILS_OPEN = re.compile(
    r"<details(\s+open(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?)?\s*>"
    r"[ \t]*(?:<summary>(.*)</summary>)?[ \t]*$",
    re.I,
)
_DETAILS_CLOSE = re.compile(r"</details>[ \t]*$", re.I)
_SUMMARY = re.compile(r"<summary>(.*)</summary>[ \t]*$", re.I)
_DELIM_CELL = re.compile(r":?-+:?")
_MAX_DEST, _MAX_TITLE, _MAX_PARENS = 4096, 1024, 32  # bound link scans (cmark uses 32 parens)
_MAX_DEPTH = 32  # container nesting limit

_SPECIAL = re.compile(r"[\\`*_~!\[<&\n]|(?<![A-Za-z0-9])https?://")
_BT_RUN = re.compile(r"`+")
_AUTOLINK = re.compile(r"<(https?://[^\s<>]*)>", re.I)
_BARE_URL = re.compile(r"https?://[^\s<>\"'`\\]*")
_LOCAL = re.compile(r"(?:localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|\[::1\])(?:[:/?#]|$)", re.I)


def _local_host(host: str) -> bool:
    """Loopback URLs (the agents' local test servers) are kept as text, not links."""
    return bool(_LOCAL.match(host))
_ENTITY = re.compile(r"&(?:#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}|([A-Za-z][A-Za-z0-9]{0,31}));")
_UNESCAPE = re.compile(r"\\([!-/:-@\[-`{-~])")
_TAG = re.compile(r"<[^>]*>")
_SCHEME = re.compile(r"([a-z][a-z0-9+.\-]*):")
_CTRL_WS = re.compile(r"[\x00-\x20\x7f]+")
_DASHES = re.compile(r"-{2,}")
_LANG_JUNK = re.compile(r"[^\w+#.\-]")


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _lead(line: str) -> tuple[int, int]:
    """Return (indent width in columns, index of first non-blank char)."""
    k = len(line) - len(line.lstrip(" "))
    if line[k:k + 1] != "\t":
        return k, k
    cols = 0
    for i, ch in enumerate(line):
        if ch == " ":
            cols += 1
        elif ch == "\t":
            cols += 4 - cols % 4
        else:
            return cols, i
    return cols, len(line)


def _strip_cols(line: str, n: int) -> str:
    """Remove up to ``n`` columns of leading whitespace (tabs count to next stop of 4)."""
    k = len(line) - len(line.lstrip(" "))
    if k >= n or line[k:k + 1] != "\t":
        return line[min(k, n):]
    cols = 0
    for i, ch in enumerate(line):
        if cols >= n:
            return line[i:]
        if ch == " ":
            cols += 1
        elif ch == "\t":
            w = 4 - cols % 4
            if cols + w > n:
                return " " * (cols + w - n) + line[i + 1:]
            cols += w
        else:
            return line[i:]
    return ""


def _fence_open(rest: str) -> Optional[tuple[str, str]]:
    m = _FENCE.match(rest)
    if not m:
        return None
    marker, info = m.group(1), m.group(2).strip()
    if marker[0] == "`" and "`" in info:
        return None
    return marker, info


def _fence_closes(rest: str, marker: str) -> bool:
    t = rest.rstrip(" \t")
    return len(t) >= len(marker) and not t.strip(marker[0])


def _item(line: str) -> Optional[tuple[int, str, int, int, str]]:
    """Match a list item: (indent, kind, start, content column, first-line content)."""
    cols, k = _lead(line)
    rest = line[k:]
    if not rest or (cols <= 3 and _HR.match(rest)):
        return None
    m = _ITEM.match(rest)
    if not m:
        return None
    kind = m.group(2) or rest[0]
    start = int(m.group(1)) if m.group(1) else 1
    width = m.end()
    after = rest[width:]
    if not after.strip():
        return cols, kind, start, cols + width + 1, ""
    spaces = len(after) - len(after.lstrip(" \t"))
    if spaces > 4:
        return cols, kind, start, cols + width + 1, after[1:]
    return cols, kind, start, cols + width + spaces, after[spaces:]


def _interrupts(line: str) -> bool:
    """True if ``line`` starts a block that may interrupt a paragraph."""
    cols, k = _lead(line)
    if cols > 3 or k == len(line):
        return False
    rest = line[k:]
    c = rest[0]
    if c in "`~":
        return _fence_open(rest) is not None
    if c == "#":
        return bool(_ATX.match(rest))
    if c == ">":
        return True
    if c == "<":
        return bool(_DETAILS_OPEN.match(rest) or _DETAILS_CLOSE.match(rest) or _SUMMARY.match(rest))
    if c in "-*_" and _HR.match(rest):
        return True
    it = _item(line)
    return bool(it and it[4].strip() and (it[1] not in ".)" or it[2] == 1))


class _Lazy:
    """Tracks whether the last fed line leaves a paragraph open (for lazy continuation)."""

    __slots__ = ("fence", "para")

    def __init__(self) -> None:
        self.fence: Optional[str] = None
        self.para = False

    def feed(self, line: str) -> None:
        cols, k = _lead(line)
        rest = line[k:]
        if self.fence:
            if cols <= 3 and _fence_closes(rest, self.fence):
                self.fence = None
            self.para = False
            return
        if not rest:
            self.para = False
            return
        if cols <= 3:
            f = _fence_open(rest)
            if f:
                self.fence, self.para = f[0], False
                return
            if rest[0] == ">":
                self.para = bool(rest.lstrip(">").strip())
                return
            if _interrupts(line):
                it = _item(line)
                self.para = bool(it and it[4].strip())
                return
        it = _item(line)
        self.para = bool(it[4].strip()) if it else True


def _split_row(row: str) -> list[str]:
    """Split a GFM table row on unescaped pipes; ``\\|`` becomes a literal pipe."""
    t = row.strip()
    cells: list[str] = []
    cur: list[str] = []
    i, n, last_sep = 0, len(t), False
    while i < n:
        ch = t[i]
        last_sep = False
        if ch == "\\" and i + 1 < n:
            cur.append("|" if t[i + 1] == "|" else t[i:i + 2])
            i += 2
            continue
        if ch == "|":
            cells.append("".join(cur))
            cur = []
            last_sep = True
        else:
            cur.append(ch)
        i += 1
    cells.append("".join(cur))
    if t.startswith("|"):
        cells.pop(0)
    if last_sep and cells:
        cells.pop()
    return [c.strip() for c in cells]


def _table_head(lines: list[str], i: int) -> Optional[tuple[list[str], list[Optional[str]]]]:
    """Return (header cells, alignments) if lines[i:i+2] start a GFM table."""
    if i + 1 >= len(lines) or "|" not in lines[i] or "|" not in lines[i + 1]:
        return None
    if _lead(lines[i])[0] > 3 or _lead(lines[i + 1])[0] > 3:
        return None
    delims = _split_row(lines[i + 1])
    if not delims or not all(_DELIM_CELL.fullmatch(d) for d in delims):
        return None
    head = _split_row(lines[i])
    if len(head) != len(delims):
        return None
    aligns: list[Optional[str]] = []
    for d in delims:
        left, right = d.startswith(":"), d.endswith(":")
        aligns.append("center" if left and right else "left" if left else "right" if right else None)
    return head, aligns


def _safe_url(url: str, *, image: bool = False) -> str:
    probe = _CTRL_WS.sub("", url).lower()
    m = _SCHEME.match(probe)
    if m:
        scheme = m.group(1)
        if scheme in ("javascript", "vbscript"):
            return "#"
        if scheme == "data" and (
            not probe.startswith("data:image/") or (not image and probe.startswith("data:image/svg"))
        ):
            return "#"
    return url.replace(" ", "%20")


def _unescape(s: str) -> str:
    return html.unescape(_UNESCAPE.sub(r"\1", s))


def _plain(fragment: str) -> str:
    """Plain text of an inline HTML fragment produced by this module."""
    return html.unescape(_TAG.sub("", fragment.replace("<br>", " ")))


def _is_punct(ch: str) -> bool:
    return ch in _ASCII_PUNCT or unicodedata.category(ch)[0] in "PS"


def _collapse(s: str) -> str:
    return " ".join(s.split())


class _Delim:
    """A run of ``*``, ``_`` or ``~~`` in the inline token stream."""

    __slots__ = ("char", "count", "orig", "can_open", "can_close", "pre", "post", "prev", "next")

    def __init__(self, char: str, count: int, can_open: bool, can_close: bool) -> None:
        self.char, self.count, self.orig = char, count, count
        self.can_open, self.can_close = can_open, can_close
        self.pre = self.post = ""
        self.prev: Optional[_Delim] = None
        self.next: Optional[_Delim] = None

    def html(self) -> str:
        return self.post + self.char * self.count + self.pre


def _unlink(d: _Delim) -> None:
    if d.prev:
        d.prev.next = d.next
    if d.next:
        d.next.prev = d.prev
    d.prev = d.next = None


def _process_emphasis(delims: list[_Delim]) -> None:
    """CommonMark 'process emphasis' over a doubly linked delimiter list."""
    for a, b in zip(delims, delims[1:]):
        a.next, b.prev = b, a
    bottom: dict[tuple[str, bool, int], Optional[_Delim]] = {}
    closer = delims[0] if delims else None
    while closer is not None:
        if not closer.can_close:
            closer = closer.next
            continue
        key = (closer.char, closer.can_open, closer.orig % 3)
        floor = bottom.get(key)
        opener = closer.prev
        while opener is not None and opener is not floor:
            if opener.char == closer.char and opener.can_open:
                if closer.char == "~":
                    break
                odd = (opener.can_close or closer.can_open) and (opener.orig + closer.orig) % 3 == 0
                if not odd or (opener.orig % 3 == 0 and closer.orig % 3 == 0):
                    break
            opener = opener.prev
        if opener is None or opener is floor:
            bottom[key] = closer.prev
            nxt = closer.next
            if not closer.can_open:
                _unlink(closer)
            closer = nxt
            continue
        if closer.char == "~":
            use, tag = 2, "del"
        else:
            use = 2 if opener.count >= 2 and closer.count >= 2 else 1
            tag = "strong" if use == 2 else "em"
        opener.count -= use
        closer.count -= use
        opener.pre = f"<{tag}>" + opener.pre
        closer.post += f"</{tag}>"
        mid = opener.next
        while mid is not None and mid is not closer:
            nxt = mid.next
            _unlink(mid)
            mid = nxt
        if opener.count == 0:
            _unlink(opener)
        if closer.count == 0:
            nxt = closer.next
            _unlink(closer)
            closer = nxt


def _scan_spans(s: str) -> tuple[dict[int, tuple[int, int, int]], dict[int, int]]:
    """Pre-pass: code spans {start: (content start, content end, end)} and matched brackets."""
    runs: dict[int, list[int]] = {}
    for m in _BT_RUN.finditer(s):
        runs.setdefault(m.end() - m.start(), []).append(m.start())
    code: dict[int, tuple[int, int, int]] = {}
    brackets: dict[int, int] = {}
    stack: list[int] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "`":
            j = i
            while j < n and s[j] == "`":
                j += 1
            lst = runs.get(j - i)
            k = bisect_left(lst, j) if lst else 0
            if lst and k < len(lst):
                close = lst[k]
                code[i] = (j, close, close + j - i)
                i = close + j - i
            else:
                i = j
            continue
        if c == "[":
            stack.append(i)
        elif c == "]" and stack:
            brackets[stack.pop()] = i
        i += 1
    return code, brackets


def _skip_ws(s: str, i: int) -> int:
    n = len(s)
    while i < n and s[i] in " \t\n":
        i += 1
    return i


def _link_tail(s: str, p: int) -> Optional[tuple[str, Optional[str], int]]:
    """Parse ``(dest "title")`` starting at the ``(`` at index p."""
    n = len(s)
    i = _skip_ws(s, p + 1)
    if i < n and s[i] == "<":
        j, stop = i + 1, min(n, i + _MAX_DEST)
        while j < stop and s[j] not in "<>\n":
            j += 2 if s[j] == "\\" else 1
        if j >= stop or s[j] != ">":
            return None
        dest, i = s[i + 1:j], j + 1
    else:
        j, depth, stop = i, 0, min(n, i + _MAX_DEST)
        while j < stop:
            c = s[j]
            if c == "\\" and j + 1 < n:
                j += 2
                continue
            if c.isspace() or ord(c) < 0x20:
                break
            if c == "(":
                depth += 1
                if depth > _MAX_PARENS:
                    return None
            elif c == ")":
                if depth == 0:
                    break
                depth -= 1
            j += 1
        if depth or j == stop < n:
            return None
        dest, i = s[i:j], j
    k = _skip_ws(s, i)
    title = None
    if k > i and k < n and s[k] in "\"'(":
        close = ")" if s[k] == "(" else s[k]
        j, stop = k + 1, min(n, k + _MAX_TITLE)
        while j < stop and s[j] != close:
            j += 2 if s[j] == "\\" else 1
        if j >= stop:
            return None
        title, k = s[k + 1:j], _skip_ws(s, j + 1)
    if k < n and s[k] == ")":
        return dest, title, k + 1
    return None


def _trim_url(url: str) -> str:
    end = len(url)
    paren = url.count("(") - url.count(")")
    square = url.count("[") - url.count("]")
    while end:
        c = url[end - 1]
        if c in ".,;:!?*_~'\"":
            end -= 1
        elif c == ")" and paren < 0:
            end, paren = end - 1, paren + 1
        elif c == "]" and square < 0:
            end, square = end - 1, square + 1
        else:
            break
    return url[:end]


class _Renderer:
    def __init__(self, link: LinkFn = None, id_prefix: str = "", heading_ids: bool = True) -> None:
        self.link = link
        self.id_prefix = id_prefix
        self.heading_ids = heading_ids
        self.slugs: set[str] = set()
        self.slug_next: dict[str, int] = {}
        self.depth = 0

    def _href(self, raw: str, *, image: bool = False) -> tuple[str, bool]:
        if self.link is not None:
            new = self.link(raw)
            if new is not None:
                raw = new
        url = _safe_url(raw, image=image)
        external = url.lower().startswith(("http://", "https://"))
        return _esc(url), external

    def _anchor(self, raw: str, label: str, title: Optional[str] = None) -> str:
        href, external = self._href(raw)
        attrs = f' href="{href}"'
        if title:
            attrs += f' title="{_esc(title)}"'
        if external:
            attrs += ' rel="noopener"'
        return f"<a{attrs}>{label}</a>"

    def inline(self, s: str, allow_links: bool = True, nested: bool = False) -> str:
        code, brackets = _scan_spans(s)
        toks: list = []
        delims: list[_Delim] = []
        buf: list[str] = []
        n, i = len(s), 0

        def flush() -> None:
            if buf:
                toks.append(_esc("".join(buf)))
                buf.clear()

        while i < n:
            m = _SPECIAL.search(s, i)
            if not m:
                buf.append(s[i:])
                break
            p = m.start()
            if p > i:
                buf.append(s[i:p])
            c = s[p]
            i = p + 1
            if c == "\\":
                nx = s[p + 1] if p + 1 < n else ""
                if nx == "\n":
                    text = "".join(buf).rstrip(" ")
                    buf.clear()
                    buf.append(text)
                    flush()
                    toks.append("<br>\n")
                    i = p + 2
                    while i < n and s[i] in " \t":
                        i += 1
                elif nx and nx in _ASCII_PUNCT:
                    buf.append(nx)
                    i = p + 2
                else:
                    buf.append("\\")
            elif c == "\n":
                text = "".join(buf)
                stripped = text.rstrip(" ")
                buf.clear()
                buf.append(stripped)
                flush()
                toks.append("<br>\n" if len(text) - len(stripped) >= 2 else "\n")
                while i < n and s[i] in " \t":
                    i += 1
            elif c == "`":
                span = code.get(p)
                if span:
                    body = s[span[0]:span[1]].replace("\n", " ")
                    if len(body) > 2 and body[0] == " " and body[-1] == " " and body.strip(" "):
                        body = body[1:-1]
                    flush()
                    toks.append(f"<code>{_esc(body)}</code>")
                    i = span[2]
                else:
                    j = p
                    while j < n and s[j] == "`":
                        j += 1
                    buf.append(s[p:j])
                    i = j
            elif c in "*_~":
                j = p
                while j < n and s[j] == c:
                    j += 1
                count = j - p
                i = j
                if c == "~" and count != 2:
                    buf.append(s[p:j])
                    continue
                before = s[p - 1] if p > 0 else " "
                after = s[j] if j < n else " "
                left = not after.isspace() and (
                    not _is_punct(after) or before.isspace() or _is_punct(before))
                right = not before.isspace() and (
                    not _is_punct(before) or after.isspace() or _is_punct(after))
                if c == "_":
                    can_open = left and (not right or _is_punct(before))
                    can_close = right and (not left or _is_punct(after))
                else:
                    can_open, can_close = left, right
                if not (can_open or can_close):
                    buf.append(s[p:j])
                    continue
                flush()
                d = _Delim(c, count, can_open, can_close)
                toks.append(d)
                delims.append(d)
            elif c == "!" or c == "[":
                image = c == "!"
                b = p + 1 if image else p
                if image and not (b < n and s[b] == "["):
                    buf.append("!")
                    continue
                q = brackets.get(b)
                tail = _link_tail(s, q + 1) if q is not None and q + 1 < n and s[q + 1] == "(" else None
                if tail is None or (not image and not allow_links):
                    buf.append(c)
                    continue
                dest, title, end = tail
                label = s[b + 1:q]
                flush()
                if image:
                    alt = _unescape(label) if nested else _plain(self.inline(label, False, True))
                    src, _ = self._href(_unescape(dest), image=True)
                    t = f' title="{_esc(_unescape(title))}"' if title else ""
                    toks.append(f'<img src="{src}" alt="{_esc(alt)}"{t} loading="lazy" decoding="async">')
                else:
                    toks.append(self._anchor(
                        _unescape(dest), self.inline(label, allow_links=False, nested=True),
                        _unescape(title) if title else None))
                i = end
            elif c == "<":
                am = _AUTOLINK.match(s, p) if allow_links else None
                if am and _local_host(am.group(1).split("://", 1)[1]):
                    buf.append(am.group(0))
                    i = am.end()
                elif am:
                    flush()
                    toks.append(self._anchor(am.group(1), _esc(am.group(1))))
                    i = am.end()
                else:
                    buf.append("<")
            elif c == "&":
                em = _ENTITY.match(s, p)
                if em and (em.group(1) is None or em.group(1) + ";" in html5):
                    flush()
                    toks.append(em.group(0))
                    i = em.end()
                else:
                    buf.append("&")
            else:  # bare http(s) URL
                um = _BARE_URL.match(s, p) if allow_links else None
                url = _trim_url(um.group(0)) if um else ""
                host = url.split("://", 1)[1] if "://" in url else ""
                if _local_host(host):  # e.g. the reviewers' http://localhost:8702/: dead off their machine
                    buf.append(url)
                    i = p + len(url)
                elif host[:1].isalnum():
                    flush()
                    toks.append(self._anchor(url, _esc(url)))
                    i = p + len(url)
                else:
                    buf.append(c)
        flush()
        if delims:
            _process_emphasis(delims)
        return "".join(t if isinstance(t, str) else t.html() for t in toks)

    def parse(self, lines: list[str], i: int = 0, in_details: bool = False) -> tuple[list[tuple], int]:
        """Parse block nodes ``(kind, start, end, *payload)`` from lines[i:]."""
        self.depth += 1
        try:
            return self._parse(lines, i, in_details, self.depth < _MAX_DEPTH)
        finally:
            self.depth -= 1

    def _parse(self, lines: list[str], i: int, in_details: bool, nest: bool) -> tuple[list[tuple], int]:
        nodes: list[tuple] = []
        n = len(lines)
        while i < n:
            line = lines[i]
            cols, k = _lead(line)
            if k == len(line):
                i += 1
                continue
            rest = line[k:]
            start = i
            if cols <= 3:
                c = rest[0]
                fence = _fence_open(rest) if c in "`~" else None
                if fence:
                    marker, info = fence
                    body: list[str] = []
                    i += 1
                    while i < n:
                        c2, k2 = _lead(lines[i])
                        if c2 <= 3 and _fence_closes(lines[i][k2:], marker):
                            i += 1
                            break
                        body.append(_strip_cols(lines[i], cols))
                        i += 1
                    lang = _LANG_JUNK.sub("", _unescape(info.split()[0])) if info else ""
                    nodes.append(("code", start, i, lang, "".join(b + "\n" for b in body)))
                    continue
                if c == "<":
                    m = _DETAILS_OPEN.match(rest) if nest else None
                    if m:
                        summary = m.group(2)
                        i += 1
                        if summary is None:
                            j = i
                            while j < n and not lines[j].strip():
                                j += 1
                            if j < n and _lead(lines[j])[0] <= 3:
                                sm = _SUMMARY.match(lines[j].lstrip(" \t"))
                                if sm:
                                    summary, i = sm.group(1), j + 1
                        children, i = self.parse(lines, i, True)
                        nodes.append(("details", start, i, bool(m.group(1)), summary, children))
                        continue
                    if _DETAILS_CLOSE.match(rest):
                        if in_details:
                            return nodes, i + 1
                        i += 1
                        continue
                    sm = _SUMMARY.match(rest)
                    if sm:
                        nodes.append(("p", start, i + 1, sm.group(1)))
                        i += 1
                        continue
                if c == "#":
                    m = _ATX.match(rest)
                    if m:
                        text = m.group(2).rstrip(" \t")
                        bare = text.rstrip("#")
                        if not bare:
                            text = ""
                        elif bare[-1] in " \t":
                            text = bare.rstrip(" \t")
                        nodes.append(("h", start, i + 1, len(m.group(1)), text))
                        i += 1
                        continue
                if c in "-*_" and _HR.match(rest):
                    nodes.append(("hr", start, i + 1))
                    i += 1
                    continue
                if c == ">" and nest:
                    i = self._quote(lines, i, nodes)
                    continue
            if nest and _item(line):
                i = self._list(lines, i, nodes)
                continue
            head = _table_head(lines, i)
            if head:
                i = self._table(lines, i, head, nodes)
                continue
            para = [rest]
            i += 1
            while i < n:
                nxt = lines[i]
                if not nxt.strip() or _interrupts(nxt) or _table_head(lines, i):
                    break
                para.append(nxt.lstrip(" \t"))
                i += 1
            nodes.append(("p", start, i, "\n".join(para).rstrip(" \t")))
        return nodes, i

    def _quote(self, lines: list[str], i: int, nodes: list[tuple]) -> int:
        start, n = i, len(lines)
        inner: list[str] = []
        lazy = _Lazy()
        while i < n:
            line = lines[i]
            cols, k = _lead(line)
            if cols <= 3 and k < len(line) and line[k] == ">":
                t = line[k + 1:]
                if t[:1] in (" ", "\t"):
                    t = t[1:]
            elif k < len(line) and lazy.para and not _interrupts(line) and not _item(line):
                t = line
            else:
                break
            inner.append(t)
            lazy.feed(t)
            i += 1
        if not any(t.strip(" \t>") for t in inner):
            # Only '>' markers (e.g. a '>>>' end-of-quote sentinel): keep it as visible text.
            nodes.append(("p", start, i, "\n".join(l.strip() for l in lines[start:i])))
            return i
        children, _ = self.parse(inner)
        nodes.append(("quote", start, i, children))
        return i

    def _list(self, lines: list[str], i: int, nodes: list[tuple]) -> int:
        start, n = i, len(lines)
        cur = _item(lines[i])
        assert cur is not None
        kind, first_num = cur[1], cur[2]
        items: list[list[tuple]] = []
        loose = False
        while True:
            cols, _, _, ccol, first = cur
            thr = min(ccol, cols + 2)
            body = [first]
            lazy = _Lazy()
            lazy.feed(first)
            j = i + 1
            while j < n:
                line = lines[j]
                c, k = _lead(line)
                if k == len(line):
                    body.append("")
                elif c >= thr:
                    body.append(_strip_cols(line, min(c, ccol)))
                elif body[-1] and lazy.para and not _item(line) and not _interrupts(line):
                    body.append(line)
                else:
                    break
                lazy.feed(body[-1])
                j += 1
            trail = 0
            while body and not body[-1]:
                body.pop()
                trail += 1
            children, _ = self.parse(body)
            if any(b[1] > a[2] for a, b in zip(children, children[1:])):
                loose = True
            items.append(children)
            nxt = _item(lines[j]) if j < n else None
            if nxt is None or nxt[1] != kind or nxt[0] >= thr:
                break
            if trail:
                loose = True
            cur, i = nxt, j
        nodes.append(("list", start, j, kind, first_num, loose, items))
        return j

    def _table(self, lines: list[str], i: int, head, nodes: list[tuple]) -> int:
        cells, aligns = head
        start, n, width = i, len(lines), len(cells)
        rows: list[list[str]] = []
        i += 2
        while i < n:
            line = lines[i]
            if not line.strip() or "|" not in line or _interrupts(line):
                break
            row = _split_row(line)[:width]
            rows.append(row + [""] * (width - len(row)))
            i += 1
        nodes.append(("table", start, i, cells, aligns, rows))
        return i

    def _slug(self, text: str) -> str:
        base = slugify(text)
        slug, k = base, self.slug_next.get(base, 2)
        while slug in self.slugs:
            slug, k = f"{base}-{k}", k + 1
        self.slugs.add(slug)
        self.slug_next[base] = k
        return slug

    def html(self, nodes: list[tuple], tight: bool = False) -> list[str]:
        out: list[str] = []
        for node in nodes:
            kind = node[0]
            if kind == "p":
                body = self.inline(node[3])
                out.append(body if tight else f"<p>{body}</p>")
            elif kind == "h":
                level, body = node[3], self.inline(node[4])
                attr = ""
                if self.heading_ids:
                    attr = f' id="{_esc(self.id_prefix + self._slug(_plain(body)))}"'
                out.append(f"<h{level}{attr}>{body}</h{level}>")
            elif kind == "hr":
                out.append("<hr>")
            elif kind == "code":
                cls = f' class="language-{_esc(node[3])}"' if node[3] else ""
                out.append(f"<pre><code{cls}>{_esc(node[4])}</code></pre>")
            elif kind == "quote":
                out.append("\n".join(["<blockquote>", *self.html(node[3]), "</blockquote>"]))
            elif kind == "details":
                parts = ["<details open>" if node[3] else "<details>"]
                if node[4] is not None:
                    parts.append(f"<summary>{self.inline(node[4].strip())}</summary>")
                parts += self.html(node[5])
                parts.append("</details>")
                out.append("\n".join(parts))
            elif kind == "list":
                out.append(self._list_html(node))
            elif kind == "table":
                out.append(self._table_html(node))
        return out

    def _list_html(self, node: tuple) -> str:
        _, _, _, kind, first_num, loose, items = node
        ordered = kind in ".)"
        tag = "ol" if ordered else "ul"
        parts = [f'<ol start="{first_num}">' if ordered and first_num != 1 else f"<{tag}>"]
        for children in items:
            inner = self.html(children, tight=not loose)
            if not inner:
                parts.append("<li></li>")
            elif not loose and children[0][0] == "p":
                rest = "\n" + "\n".join(inner[1:]) + "\n" if len(inner) > 1 else ""
                parts.append(f"<li>{inner[0]}{rest}</li>")
            else:
                parts.append("\n".join(["<li>", *inner, "</li>"]))
        parts.append(f"</{tag}>")
        return "\n".join(parts)

    def _table_html(self, node: tuple) -> str:
        _, _, _, head, aligns, rows = node
        cls = [f' class="align-{a}"' if a else "" for a in aligns]
        parts = ['<div class="table-wrap" tabindex="0" role="region" aria-label="Table (scrolls horizontally)"><table>', "<thead>", "<tr>"]
        parts += [f"<th{a}>{self.inline(c)}</th>" for a, c in zip(cls, head)]
        parts += ["</tr>", "</thead>"]
        if rows:
            parts.append("<tbody>")
            for row in rows:
                parts.append("<tr>")
                parts += [f"<td{a}>{self.inline(c)}</td>" for a, c in zip(cls, row)]
                parts.append("</tr>")
            parts.append("</tbody>")
        parts.append("</table></div>")
        return "\n".join(parts)

    def text(self, nodes: list[tuple], out: list[str]) -> None:
        for node in nodes:
            kind = node[0]
            if kind == "p":
                out.append(_collapse(_plain(self.inline(node[3]))))
            elif kind == "h":
                out.append(_collapse(_plain(self.inline(node[4]))))
            elif kind == "code":
                out.append(_collapse(node[4]))
            elif kind == "quote":
                self.text(node[3], out)
            elif kind == "details":
                if node[4] is not None:
                    out.append(_collapse(_plain(self.inline(node[4]))))
                self.text(node[5], out)
            elif kind == "list":
                for children in node[6]:
                    self.text(children, out)
            elif kind == "table":
                for row in [node[3], *node[5]]:
                    out.append(_collapse(" ".join(_plain(self.inline(c)) for c in row)))


def _lines(text: str) -> list[str]:
    text = text[1:] if text.startswith("\ufeff") else text
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "\ufffd").split("\n")


def render(text: str, *, link: LinkFn = None, id_prefix: str = "", heading_ids: bool = True) -> str:
    """Render a Markdown document to an HTML fragment.

    ``link(href)`` is called for every link/image target; a returned string
    replaces it, ``None`` keeps it. Heading ids are ``id_prefix + slug``,
    deduplicated within one call.
    """
    r = _Renderer(link, id_prefix, heading_ids)
    nodes, _ = r.parse(_lines(text))
    out = r.html(nodes)
    return "\n".join(out) + "\n" if out else ""


def render_inline(text: str, *, link: LinkFn = None) -> str:
    """Render inline Markdown only (no block structure)."""
    t = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "\ufffd")
    return _Renderer(link).inline(t.strip())


def slugify(text: str) -> str:
    """Lowercase slug: NFKD-transliterated, non-alphanumeric runs become '-'."""
    chars = []
    for ch in unicodedata.normalize("NFKD", text):
        if unicodedata.combining(ch):
            continue
        chars.append(ch.lower() if ch.isalnum() else "-")
    return _DASHES.sub("-", "".join(chars)).strip("-") or "section"


def to_text(text: str) -> str:
    """Plain text of a Markdown document: one paragraph per block, blank-line separated."""
    r = _Renderer()
    nodes, _ = r.parse(_lines(text))
    out: list[str] = []
    r.text(nodes, out)
    return "\n\n".join(p for p in out if p)
