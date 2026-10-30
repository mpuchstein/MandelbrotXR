"""Page shell, URL helpers and evidence links shared by every page module.

Page modules write HTML whose internal URLs start with '@/' (the site root), e.g.
href="@/rankings/". Site.page() rewrites '@/' to the right relative prefix for the page,
so the output works at any root under python3 -m http.server. Never hard-code '../'.
"""
from __future__ import annotations

import hashlib
import html
import os
import re
import shutil
from dataclasses import dataclass, field
from functools import cached_property

from .data import Candidate, Model

GITHUB = "https://github.com/mpuchstein/MandelbrotXR"
SITE_TITLE = "MandelbrotXR results"

esc = lambda s: html.escape(str(s), quote=True)

NAV = [  # (label, root-relative path, section key)
    ("Home", "", "home"),
    ("Rankings", "rankings/", "rankings"),
    ("Candidates", "candidates/", "candidates"),
    ("Compare", "compare/", "compare"),
    ("Techniques", "techniques/", "techniques"),
    ("Judges & reviews", "judges/", "judges"),
    ("Transcripts", "transcripts/", "transcripts"),
    ("Methodology", "methodology/", "methodology"),
    ("Data", "data/", "data"),
    ("Search", "search/", "search"),
]


def transcript_id(path: str) -> str:
    """Stable transcript id for a repo-relative transcript path (see transcript_sources)."""
    parts = path.split("/")
    if path == "ReviewOrchestrator/TRANSCRIPT.md":
        return "orchestrator"
    if parts[0] == "Judge":
        return "judge-" + parts[1].removesuffix("-Judge").lower().replace("_", "-")
    if parts[0] == "Review":
        return "review-" + parts[1].removesuffix("-Review").lower().replace("_", "-") + "-" + parts[2].lower()
    if parts[:2] == ["ReviewOrchestrator", "blind"]:
        return "blind-" + parts[2]
    if parts[:2] == ["ReviewOrchestrator", "discarded"]:
        return "discarded-" + parts[2]
    if len(parts) == 2 and parts[1] == "TRANSCRIPTION.md":
        return "chat-" + parts[0].lower()
    return re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")


@dataclass
class TranscriptSource:
    id: str
    path: str       # repo-relative
    title: str
    kind: str       # "chat" | "review" | "judge" | "orchestrator" | "blind" | "discarded"
    slug: str | None = None


@dataclass
class Site:
    model: Model
    out: str
    base_url: str
    git: dict
    assets: dict = field(default_factory=dict)       # asset name -> "?v=hash" suffix
    search_docs: list = field(default_factory=list)
    pages: list = field(default_factory=list)        # every written HTML page (out-relative)
    _media: set = field(default_factory=set)

    @property
    def repo(self) -> str:
        return self.model.repo

    # ------------------------------------------------------------ urls
    def gh(self, path: str, line: int | None = None, *, tree: bool = False) -> str:
        """Permanent GitHub URL of a repo path at the build commit."""
        kind = "tree" if tree else "blob"
        return f"{GITHUB}/{kind}/{self.git['sha']}/{path}" + (f"#L{line}" if line else "")

    def abs_url(self, path: str) -> str:
        """Absolute URL (only for QR codes, the feed and canonical links)."""
        return self.base_url.rstrip("/") + "/" + path.lstrip("/")

    def transcript_sources(self) -> list[TranscriptSource]:
        m, out = self.model, []
        for c in m.candidates:
            out.append(TranscriptSource(transcript_id(c.transcription), c.transcription, f"Chat transcript — {c.name}", "chat", c.slug))
        for r in m.reviews:
            if "TRANSCRIPT.md" in r.files:
                p = r.files["TRANSCRIPT.md"]
                out.append(TranscriptSource(transcript_id(p), p, f"{r.type_label} review agent log — {m.cand(r.slug).name}", "review", r.slug))
        for j in m.judges:
            if "TRANSCRIPT.md" in j.files:
                p = j.files["TRANSCRIPT.md"]
                out.append(TranscriptSource(transcript_id(p), p, f"{j.label} judge agent log", "judge"))
        if os.path.isfile(os.path.join(self.repo, "ReviewOrchestrator/TRANSCRIPT.md")):
            out.append(TranscriptSource("orchestrator", "ReviewOrchestrator/TRANSCRIPT.md", "Orchestrator session log", "orchestrator"))
        bdir = os.path.join(self.repo, "ReviewOrchestrator/blind")
        for nn in sorted(os.listdir(bdir)) if os.path.isdir(bdir) else []:
            p = f"ReviewOrchestrator/blind/{nn}/TRANSCRIPT.md"
            if os.path.isfile(os.path.join(self.repo, p)):
                out.append(TranscriptSource(transcript_id(p), p, f"Anonymized transcript as reviewers saw it — {nn}", "blind", m.blind.get(nn)))
        for d in m.discarded:
            if "TRANSCRIPT.md" in d["files"]:
                p = d["files"]["TRANSCRIPT.md"]
                out.append(TranscriptSource(transcript_id(p), p, f"Discarded run agent log — {d['id']}", "discarded"))
        return out

    @cached_property
    def _tids(self) -> dict[str, str]:
        return {t.path: t.id for t in self.transcript_sources()}

    def local(self, path: str) -> str:
        """Root-relative URL ('@/…') of the locally rendered copy of a repo path.
        Transcripts -> transcripts/<id>/, images -> media/<path>, other text files -> source/<path>.html,
        a product HTML -> play/<slug>/, a directory -> source/<dir>/ (listing)."""
        if path in self._tids:
            return f"@/transcripts/{self._tids[path]}/"
        for c in self.model.candidates:
            if path == c.html_path:
                return f"@/play/{c.slug}/"
        if path.lower().endswith((".jpg", ".jpeg", ".png")):
            return "@/" + self.media(path)
        if os.path.isdir(os.path.join(self.repo, path)):
            return f"@/source/{path.strip('/')}/"
        return f"@/source/{path}.html"

    def media(self, path: str) -> str:
        """Copy an image byte-for-byte to media/<path> (once) and return its out-relative path."""
        if path not in self._media:
            dst = os.path.join(self.out, "media", path)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(self.repo, path), dst)
            self._media.add(path)
        return f"media/{path}"

    def evidence(self, path: str, label: str | None = None, *, anchor: str = "", line: int | None = None) -> str:
        """'label' linking to the local copy, plus a 'GitHub' link to the blob at the build commit."""
        label = label or path
        return (f'<span class="evidence"><a href="{esc(self.local(path))}{esc(anchor)}">{esc(label)}</a>'
                f' <a class="gh" href="{esc(self.gh(path, line))}" rel="noopener" title="{esc(path)} on GitHub at {self.git["sha"][:7]}">GitHub</a></span>')

    # ------------------------------------------------------------ output
    def write(self, rel: str, content: str | bytes) -> None:
        dst = os.path.join(self.out, rel)
        os.makedirs(os.path.dirname(dst) or self.out, exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(dst, mode, **({} if isinstance(content, bytes) else {"encoding": "utf-8", "newline": "\n"})) as f:
            f.write(content)

    @staticmethod
    def prefix(rel: str) -> str:
        depth = rel.count("/")
        return "../" * depth if depth else "./"

    def asset(self, name: str) -> str:
        return f"@/assets/{name}{self.assets.get(name, '')}"

    def page(self, rel: str, title: str, body: str, *, section: str = "", crumbs: list[tuple[str, str]] | None = None,
             description: str = "", scripts: list[str] = (), head: str = "", wide: bool = False) -> None:
        """Write a complete site page.
        rel: out-relative file path ending in index.html (e.g. 'rankings/index.html').
        crumbs: [(label, root-relative path or '')] after Home; the last one is the current page.
        scripts: JS asset names under assets/js/ (e.g. 'rankings.js'), loaded with defer."""
        assert rel.endswith(".html"), rel
        canonical = self.abs_url(rel.removesuffix("index.html"))
        nav = "".join(
            f'<li><a href="@/{p}"{" aria-current=\"page\"" if key == section else ""}>{esc(label)}</a></li>' for label, p, key in NAV)
        trail = [("Home", "")] + list(crumbs or [])
        bc = ""
        if len(trail) > 1:
            items = []
            for i, (label, p) in enumerate(trail):
                if i == len(trail) - 1:
                    items.append(f'<li><span aria-current="page">{esc(label)}</span></li>')
                else:
                    items.append(f'<li><a href="@/{p}">{esc(label)}</a></li>')
            bc = f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{"".join(items)}</ol></nav>'
        g = self.git
        js = "".join(f'<script src="{self.asset("js/" + s)}" defer></script>' for s in scripts)
        full_title = title if title == SITE_TITLE else f"{title} · {SITE_TITLE}"
        doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description or 'Eight AI coding assistants built a WebXR Mandelbrot room; blind reviews and judges ranked them.')}">
<meta name="color-scheme" content="light dark">
<link rel="canonical" href="{esc(canonical)}">
<link rel="icon" href="{self.asset('favicon.svg')}" type="image/svg+xml">
<link rel="stylesheet" href="{self.asset('site.css')}">
<link rel="alternate" type="application/atom+xml" title="MandelbrotXR changes" href="@/feed.xml">
<script src="{self.asset('js/theme.js')}"></script>
{js}{head}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
<div class="bar">
<a class="brand" href="@/"><span class="brand-mark" aria-hidden="true"></span>MandelbrotXR <span class="brand-sub">results</span></a>
<button class="theme-toggle" type="button" id="theme-toggle" aria-pressed="false" hidden><span class="theme-icon" aria-hidden="true"></span>Dark theme</button>
</div>
<nav class="site-nav" aria-label="Main"><ul>{nav}</ul></nav>
</header>
<main id="main" class="{'wide' if wide else ''}">
{bc}
{body}
</main>
<footer class="site-footer">
<p>Built from commit <a href="{GITHUB}/commit/{g['sha']}" rel="noopener"><code>{esc(g['version'][:12] + ('…-dirty' if g['dirty'] else ''))}</code></a> of <a href="{GITHUB}" rel="noopener">mpuchstein/MandelbrotXR</a>, committed {esc(g['date'])}.
Static site; no cookies, no analytics, no third-party requests.</p>
<p><a href="@/data/">Data &amp; schema</a> · <a href="@/data/changelog/">Changelog</a> · <a href="@/feed.xml">Atom feed</a> · <a href="@/methodology/">Methodology &amp; caveats</a></p>
</footer>
</body>
</html>
"""
        pre = self.prefix(rel)
        doc = doc.replace('="@/', f'="{pre}').replace("='@/", f"='{pre}")
        if "@/" in re.sub(r"<(pre|code)\b.*?</\1>", "", doc, flags=re.S) and re.search(r'(?:href|src|action|data-[a-z-]+)="@/', doc):
            raise AssertionError(f"{rel}: unrewritten @/ link")
        self.write(rel, doc)
        self.pages.append(rel)

    def search_doc(self, url: str, title: str, kind: str, context: str, text: str) -> None:
        """Register a document for the client-side search index. url is root-relative (no '@/')."""
        self.search_docs.append({"url": url.removeprefix("@/"), "title": title, "kind": kind, "context": context, "text": text})


# ---------------------------------------------------------------- shared fragments

def prompt_badge(prompt: str) -> str:
    return f'<span class="badge badge-{esc(prompt)}" title="Built from prompt {esc(prompt)} (prompt{esc(prompt[1:])}.txt)">{esc(prompt)}</span>'


def cand_link(c: Candidate) -> str:
    return f'<a href="@/candidates/{c.slug}/">{esc(c.name)}</a>'


def figure(site: Site, shot, *, cls: str = "shot", link: bool = True) -> str:
    """A lazy screenshot figure with explicit dimensions (no layout shift) and alt text."""
    c = site.model.cand(shot.slug) if shot.slug else None
    name = os.path.splitext(os.path.basename(shot.path))[0]
    words = re.sub(r"^[A-Z]-|^\d+-", "", name).replace("-", " ").replace("_", " ")
    alt = f"{shot.source_label} screenshot of {c.name if c else 'a candidate'}: {words}"
    src = "@/" + site.media(shot.path)
    cap = f'<span class="cap-src">{esc(shot.source_label)} · <code>{esc(os.path.basename(shot.path))}</code></span>'
    img = f'<img src="{src}" width="{shot.width}" height="{shot.height}" alt="{esc(alt)}" loading="lazy" decoding="async">'
    if link:
        img = f'<a href="{src}">{img}</a>'
    return f'<figure class="{cls}">{img}<figcaption>{cap}</figcaption></figure>'
