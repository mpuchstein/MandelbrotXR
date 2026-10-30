"""Locally rendered copies of every other text file the site may cite (brief §11: evidence links go to
GitHub "alongside the locally rendered copy").

source/<path>.html   one page per text file (exactly the URL Site.local(path) returns); line anchors #L<n>
source/<dir>/        a listing for every directory
source/index.html    the whole tree

Not rendered here: transcripts (transcripts/…), product HTML (play/<slug>/ is the byte-identical copy),
images (media/…), and anything under .git, other dot-directories, __pycache__/ and site/ (except site/*.md and site/*.toml).
"""
from __future__ import annotations

import os
import posixpath
import re

from ..fragments import render_md
from ..data import repo_files
from ..layout import Site, esc

ORDER = 750

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico")
SKIP_DIRS = {"__pycache__", "node_modules"}
SITE_DOCS = (".md", ".toml")  # from site/ only its top-level documents (brief, README, DEPLOY, candidates.toml)


def walk(repo: str) -> tuple[list[str], list[str]]:
    """(directories, files), repo-relative, sorted; '' is the root directory. Files come from
    data.repo_files() (committed + untracked-but-not-ignored), never from ignored build output or caches."""
    files = []
    for p in sorted(repo_files(repo)):
        parts = p.split("/")
        if any(x.startswith(".") for x in parts[:-1]) or any(x in SKIP_DIRS for x in parts):
            continue
        if parts[0] == "site" and (len(parts) != 2 or not p.endswith(SITE_DOCS)):
            continue
        if p.endswith((".pyc", ".pyo")) or parts[-1] == ".DS_Store":
            continue
        files.append(p)
    dirs = {""}
    for p in files:
        d = posixpath.dirname(p)
        while d:
            dirs.add(d)
            d = posixpath.dirname(d)
    return sorted(dirs), files


def _human(b: int) -> str:
    return f"{b} B" if b < 1000 else f"{b / 1000:.1f} kB" if b < 1_000_000 else f"{b / 1_000_000:.2f} MB"


def numbered(text: str) -> str:
    """<pre class="src"> with one block per line, id="L<n>" (CSS counters draw the numbers)."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    body = "".join(f'<span id="L{i}">{esc(l)}</span>' for i, l in enumerate(lines, 1))
    return f'<pre class="src"><code>{body}</code></pre>'


def crumbs_for(path: str, last: str | None = None) -> list[tuple[str, str]]:
    out = [("Source files", "source/")]
    parts = path.split("/") if path else []
    for i, p in enumerate(parts):
        if i == len(parts) - 1 and last is not None:
            out.append((p, ""))
        else:
            out.append((p, "source/" + "/".join(parts[: i + 1]) + "/"))
    if last is None and len(out) > 1:
        out[-1] = (out[-1][0], "")
    return out


_TD_CODE = re.compile(r"(<td[^>]*>\s*<code>)([^<]*)(</code>)")


def _wbr(text_html: str) -> str:
    """Break opportunities after '/', '_' and '-' in an (already escaped) path or identifier."""
    return re.sub(r"([/_-])", r"\1<wbr>", text_html)


_INLINE_PATH = re.compile(r"(?<!<pre>)(?<!<td>)<code>([^<\s]*/[^<\s]*)</code>")


def _path_code(m: re.Match) -> str:
    """Inline code that is a path: break only after '/', never at a '-' or '_' inside a name (short segments only)."""
    segs = m.group(1).split("/")
    if max(len(x) for x in segs) > 32:
        return m.group(0)
    return "<code>" + "/<wbr>".join(f'<span class="nw">{x}</span>' if x else "" for x in segs) + "</code>"


def _sections(site: Site) -> dict[str, str]:
    """Top-level folder -> nav section, discovered from the model: candidate folders belong to Candidates,
    the review/judge/orchestration folders to Judges & reviews. Anything else stays under Transcripts."""
    out = {}
    for t in site.transcript_sources():
        if t.kind in ("review", "judge", "orchestrator", "blind"):
            out[t.path.split("/", 1)[0]] = "judges"
    for j in site.model.judges:
        out[j.dir.split("/", 1)[0]] = "judges"
    for r in site.model.reviews:
        out[r.dir.split("/", 1)[0]] = "judges"
    for c in site.model.candidates:
        out[c.folder] = "candidates"
    return out


def build(site: Site) -> None:
    repo = site.repo
    sec_of = _sections(site)
    dirs, files = walk(repo)
    transcripts = {t.path: t for t in site.transcript_sources()}
    products = {c.html_path: c for c in site.model.candidates}
    texts: dict[str, str] = {}
    kinds: dict[str, str] = {}          # path -> label shown in listings
    for f in files:
        if f in transcripts:
            kinds[f] = "transcript"
        elif f in products:
            kinds[f] = "product"
        elif f.lower().endswith(IMAGE_EXT):
            kinds[f] = "image"
        else:
            try:
                with open(os.path.join(repo, f), encoding="utf-8") as fh:
                    texts[f] = fh.read()
                kinds[f] = "text"
            except (UnicodeDecodeError, ValueError):
                kinds[f] = "binary"
    # only directories that contain something we list
    keep = {""}
    for f in files:
        d = posixpath.dirname(f)
        while d not in keep:
            keep.add(d)
            d = posixpath.dirname(d)
    dirs = [d for d in dirs if d in keep]
    sizes = {f: os.path.getsize(os.path.join(repo, f)) for f in files}

    def href(f: str) -> str:
        k = kinds[f]
        if k == "text":
            return f"@/source/{f}.html"
        if k == "binary":
            return site.gh(f)
        return site.local(f)

    def what(f: str) -> str:
        k = kinds[f]
        if k == "text":
            n = texts[f].count("\n") + (0 if texts[f].endswith("\n") or not texts[f] else 1)
            return f"{n:,} lines · {_human(sizes[f])}"
        if k == "transcript":
            return f"transcript · {_human(sizes[f])}"
        if k == "product":
            return f"product (play copy) · {_human(sizes[f])}"
        if k == "image":
            return f"image · {_human(sizes[f])}"
        return f"binary, GitHub only · {_human(sizes[f])}"

    # ---- file pages
    for f, text in texts.items():
        name = posixpath.basename(f)
        d = posixpath.dirname(f)
        head = (f'<h1 class="src-path">{esc(name)}</h1>'
                f'<ul class="tx-meta src-meta"><li><code>{_wbr(esc(f))}</code></li><li>{esc(what(f))}</li>'
                f'<li>in <a href="@/source/{d + "/" if d else ""}">{esc(d + "/" if d else "repository root")}</a></li>'
                f'<li><a href="{esc(site.gh(f))}" rel="noopener">Original on GitHub at {esc(site.git["sha"][:7])}</a></li></ul>')
        if not text.strip():
            body = head + '<p class="note">This file is empty in the repository.</p>'
        elif f.lower().endswith((".md", ".markdown")):
            doc = re.sub(r"<(/?)h([1-6])([\s>])", lambda m: f"<{m.group(1)}h{min(6, int(m.group(2)) + 1)}{m.group(3)}",
                         render_md(site, f, text, id_prefix="md-"))
            doc = _TD_CODE.sub(lambda m: m.group(1) + _wbr(m.group(2)) + m.group(3), doc)
            doc = _INLINE_PATH.sub(_path_code, doc)
            body = (head + f'<section class="src-doc" aria-label="Rendered Markdown">{doc}</section>'
                    + '<details class="src-view"><summary>Source with line numbers</summary>' + numbered(text) + '</details>')
        else:
            body = head + numbered(text)
        site.page(f"source/{f}.html", f"{name} · {d or 'repository root'}", body, section=sec_of.get(f.split("/", 1)[0], "transcripts"),
                  crumbs=crumbs_for(f, last=name), description=f"Rendered copy of {f} from the MandelbrotXR repository.",
                  scripts=["transcripts.js"])

    # ---- directory listings
    children: dict[str, tuple[list[str], list[str]]] = {d: ([], []) for d in dirs}
    for d in dirs:
        if d:
            children[posixpath.dirname(d)][0].append(d)
    for f in files:
        children[posixpath.dirname(f)][1].append(f)

    def count_files(d: str) -> int:
        pre = d + "/" if d else ""
        return sum(1 for f in files if f.startswith(pre))

    def listing(d: str) -> str:
        sub, fs = children[d]
        items = [f'<li><a href="@/source/{s}/">{esc(posixpath.basename(s))}/</a><span class="what">{count_files(s)} files</span></li>' for s in sub]
        items += [f'<li><a href="{esc(href(f))}">{esc(posixpath.basename(f))}</a><span class="what">{esc(what(f))}</span></li>' for f in fs]
        return f'<ul class="dir-list">{"".join(items)}</ul>'

    def tree(d: str) -> str:
        sub, fs = children[d]
        items = [f'<li class="dir"><a href="@/source/{s}/">{esc(posixpath.basename(s))}/</a>{tree(s)}</li>' for s in sub]
        items += [f'<li><a href="{esc(href(f))}">{esc(posixpath.basename(f))}</a> <span class="muted">{esc(what(f))}</span></li>' for f in fs]
        return f'<ul>{"".join(items)}</ul>' if items else ""

    for d in dirs:
        if not d:
            continue
        up = posixpath.dirname(d)
        body = (f'<h1 class="src-path">{esc(posixpath.basename(d))}/</h1>'
                f'<p class="muted src-meta"><code>{esc(d)}/</code> · <a href="@/source/{up + "/" if up else ""}">up to {esc(up or "repository root")}</a>'
                f' · <a href="{esc(site.gh(d, tree=True))}" rel="noopener">on GitHub</a></p>' + listing(d))
        site.page(f"source/{d}/index.html", f"{d}/", body, section=sec_of.get(d.split("/", 1)[0], "transcripts"), crumbs=crumbs_for(d),
                  description=f"Files in {d}/ of the MandelbrotXR repository.")

    n_text = len(texts)
    body = ('<h1>Source files</h1>'
            f'<p class="lede">Every file of the experiment record, {len(files)} in all. {n_text} text files are rendered here with '
            'line anchors (<code>#L&lt;n&gt;</code>); transcripts open in the <a href="@/transcripts/">transcript reader</a>, '
            'products open in their byte-identical <code>play/</code> copy, and images are copied unchanged.</p>'
            '<p class="note">Each page links to the same file on GitHub at the build commit. Build tooling caches '
            '(<code>__pycache__/</code>), the site generator code and output under <code>site/</code> (only its documents are listed) and dot-directories are not listed.</p>'
            '<h2>Repository root</h2>' + listing("") +
            '<h2>Full tree</h2>' + f'<div class="src-tree">{tree("")}</div>')
    site.page("source/index.html", "Source files", body, section="transcripts", crumbs=[("Source files", "")],
              description="Rendered copies of every source file in the MandelbrotXR repository.")
