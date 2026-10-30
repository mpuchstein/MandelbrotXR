"""Data and changes: data/results.json, data/ranks.csv, data/scores.csv, data/criteria.csv,
the Data page (data/) documenting their schema, the Changelog (data/changelog/) and feed.xml (Atom 1.0).

Everything is exported from the model (site/sitelib/data.py); nothing is hardcoded. The changelog and the
feed come from `git log` of Judge/ and Review/ (data.git_history): one entry per added judgment, i.e. per
added Judge/<X>-Judge/RANKING.md (a judge ranking) or Review/<T>-Review/<folder>/REVIEW.md (a review).

Determinism: explicit key order, floats rounded to fixed decimals, dates from commits only (never the wall
clock), every list in model or git order.
"""
from __future__ import annotations

import csv
import html
import io
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as xesc

from .. import md
from ..data import git_history
from ..fragments import fmt_mean, fmt_score, judge_url, review_url
from ..layout import GITHUB, Site, esc

ORDER = 850

SCHEMA_ID = "mandelbrotxr-results/1"
FEED_TITLE = "MandelbrotXR results — new judgments"
HISTORY_PATHS = ["Judge", "Review"]
DEC = 4   # decimals for every non-integer number in results.json

_JUDGE_RE = re.compile(r"^Judge/([^/]+-Judge)/RANKING\.md$")
_REVIEW_RE = re.compile(r"^Review/([^/]+-Review)/([^/]+)/REVIEW\.md$")


# ---------------------------------------------------------------- helpers

def _num(x):
    """Integral floats as int, others rounded to DEC decimals (stable repr)."""
    if x is None:
        return None
    if float(x) == int(x):
        return int(x)
    return round(float(x), DEC)


def _url(u: str) -> str:
    return u.removeprefix("@/")


def _size(n: int) -> str:
    return f"{n:,} B" if n < 1000 else f"{n / 1000:,.1f} kB"


def _csv(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", md.to_text(text)).strip()


# ---------------------------------------------------------------- results.json

def results(site: Site) -> dict:
    m, g = site.model, site.git
    cands = []
    for c in m.candidates:
        cands.append({
            "slug": c.slug, "folder": c.folder, "name": c.name, "label": c.label, "vendor": c.vendor,
            "product": c.product, "model": c.model, "effort": c.effort, "provenance": c.provenance,
            "prompt": c.prompt, "product_file": c.html_path, "source_url": c.source_url, "date": c.date,
            "bytes": c.bytes, "sha256": c.sha256, "external": list(c.external), "alert_calls": c.alert_calls,
            "blind_id": next((nn for nn, s in sorted(m.blind.items()) if s == c.slug), None),
            "transcription": c.transcription,
            "urls": {"page": f"candidates/{c.slug}/", "play": f"play/{c.slug}/", "transcript": _url(site.local(c.transcription))},
        })
    reviews = []
    for r in m.reviews:
        reviews.append({
            "type": r.type_id, "slug": r.slug, "folder": r.folder, "blind_id": r.blind_id, "title": r.title,
            "overall": _num(r.overall), "overall_line": r.overall_line,
            "criteria": [{"name": k.name, "score": _num(k.score), "reason": k.reason} for k in r.criteria],
            "files": dict(sorted(r.files.items())), "url": _url(review_url(r)),
        })
    judges = []
    for j in m.judges:
        judges.append({
            "id": j.id, "folder": j.folder, "label": j.label, "title": j.title, "material": j.material,
            "focus": j.focus, "browser": j.browser,
            "mapping": {l: j.mapping[l] for l in sorted(j.mapping)},
            "ranking": [{"rank": x.rank, "letter": x.letter, "slug": x.slug, "prompt": x.prompt,
                         "justification": x.justification} for x in j.rows],
            "special": [{"letters": s.letters, "slugs": s.slugs, "title": s.title, "reason": s.reason, "raw": s.raw}
                        for s in j.special],
            "files": dict(sorted(j.files.items())), "url": _url(judge_url(j)),
        })
    mean, spread, cover = {}, {}, {}
    for c in m.candidates:
        mr = m.mean_rank(c.slug)
        n, total = m.coverage(c.slug)
        cover[c.slug] = {"judges": n, "of": total}
        if mr is not None:
            mean[c.slug] = {"display": fmt_mean(mr), "exact": f"{mr.numerator}/{mr.denominator}", "value": _num(float(mr))}
        sp = m.spread(c.slug)
        if sp:
            spread[c.slug] = {"min": sp[0], "max": sp[1], "sd": round(sp[2], DEC)}
    standing = {s: {"place": p, "tied": t} for s, (p, t) in sorted(m.standing().items(), key=lambda kv: m.cand(kv[0]).index)}
    kendall = [{"a": a.id, "b": b.id, "tau": None if tau is None else round(tau, DEC), "n": n} for a, b, tau, n in m.kendall_pairs()]
    return {
        "schema": SCHEMA_ID,
        "build": {"commit": g["version"], "sha": g["sha"], "dirty": g["dirty"], "date": g["date_iso"],
                  "github": f"{GITHUB}/tree/{g['sha']}"},
        "candidates": cands,
        "review_types": [{"id": t, "folder": f, "label": l} for t, f, l in m.review_types],
        "reviews": reviews,
        "judges": judges,
        "derived": {"order": [c.slug for c in m.ordered()], "coverage": cover, "mean_rank": mean,
                    "standing": standing, "spread": spread, "kendall_tau_b": kendall},
    }


def csvs(site: Site) -> dict[str, str]:
    m = site.model
    ranks = [[j.id, j.label, x.letter, x.slug, m.cand(x.slug).folder, x.prompt, x.rank] for j in m.judges for x in j.rows]
    scores = [[r.type_id, r.slug, r.folder, r.blind_id, fmt_score(r.overall)] for r in m.reviews]
    crit = [[r.type_id, r.slug, i, k.name, fmt_score(k.score), k.reason]
            for r in m.reviews for i, k in enumerate(r.criteria, 1)]
    return {
        "ranks.csv": _csv(["judge", "judge_label", "letter", "slug", "folder", "prompt", "rank"], ranks),
        "scores.csv": _csv(["review_type", "slug", "folder", "blind_id", "overall"], scores),
        "criteria.csv": _csv(["review_type", "slug", "criterion_index", "criterion", "score", "reason"], crit),
    }


# ---------------------------------------------------------------- schema documentation

RESULTS_SCHEMA = [  # (field, type, meaning, derived?)
    ("schema", "string", f'Schema identifier, currently <code>{SCHEMA_ID}</code>. Changes when fields are removed or change meaning.', False),
    ("build.commit", "string", "Build commit SHA (<code>git rev-parse HEAD</code>), with <code>-dirty</code> appended if the working tree had uncommitted changes.", False),
    ("build.sha / build.dirty", "string / boolean", "The bare commit SHA and whether the tree was dirty.", False),
    ("build.date", "string", "Commit date of the build commit (ISO 8601). Never the wall clock.", False),
    ("build.github", "string", "The GitHub tree at the build commit.", False),
    ("candidates[]", "array", "One object per entry of <code>site/candidates.toml</code>, in file order.", False),
    ("candidates[].slug, folder, name, label", "string", "URL slug, top-level repo folder, display name, short table label.", False),
    ("candidates[].vendor, product, model, effort, provenance", "string", "As recorded in <code>site/candidates.toml</code> (from the transcript headers and ReviewOrchestrator/README.md §1).", False),
    ("candidates[].prompt", "string", "Prompt version the candidate was built from: <code>v0</code> = prompt0.txt, <code>v1</code> = prompt1.txt.", False),
    ("candidates[].product_file, transcription", "string", "Repo-relative paths of the product HTML and the chat transcript.", False),
    ("candidates[].source_url, date", "string", "Original chat URL and chat date (YYYY-MM-DD).", False),
    ("candidates[].bytes, sha256", "integer, string", "Size and SHA-256 of the product file; the build fails unless the SHA matches ReviewOrchestrator/blind/source-html.sha256.", False),
    ("candidates[].external, alert_calls", "array of strings, integer", "Absolute URLs the product loads as resources, and its number of <code>alert(</code> calls, found by scanning the file.", True),
    ("candidates[].blind_id", "string | null", "Phase-1 blind label (<code>candidate-NN</code>) from ReviewOrchestrator/blind-mapping.json.", False),
    ("candidates[].urls", "object", "Site paths (relative to the site root) of the candidate page, the playable copy and the rendered transcript.", False),
    ("review_types[]", "array", "<code>{id, folder, label}</code> for every <code>Review/*-Review/</code> folder.", False),
    ("reviews[]", "array", "One object per phase-1 review, by review type, then folder.", False),
    ("reviews[].type, slug, folder, blind_id, title", "string", "Review type id, candidate, its folder, the blind label the reviewer saw and the review's H1 as written.", False),
    ("reviews[].overall", "number", "Overall score (1–10): the first number on the overall-score line.", False),
    ("reviews[].overall_line", "string", "That line, verbatim, so the parse can be checked.", False),
    ("reviews[].criteria[]", "array", "<code>{name, score, reason}</code> per row of the criteria table, in table order. <code>reason</code> is the reviewer's Markdown cell, verbatim.", False),
    ("reviews[].files, url", "object, string", "Repo-relative paths of PROMPT.txt, REVIEW.md, TRANSCRIPT.md; site path of the review page.", False),
    ("judges[]", "array", "One object per phase-2 judge (Judge/*-Judge/ with a RANKING.md and a judge-mapping.json entry).", False),
    ("judges[].id, folder, label, title", "string", "Judge id (folder name lowercased, <code>-Judge</code> stripped), folder, label, RANKING.md H1.", False),
    ("judges[].material, focus", "string | null", "Material and special-elements focus from the Judges table of Judge/README.md.", False),
    ("judges[].browser", "boolean", "Hands-on in a browser (id contains <code>browser</code> or the folder has screenshots) vs. static material only.", False),
    ("judges[].mapping", "object", "Letter → candidate slug, from Judge/judge-mapping.json.", False),
    ("judges[].ranking[]", "array", "<code>{rank, letter, slug, prompt, justification}</code> per row of the judge's ranking table, best first. <code>justification</code> is verbatim Markdown.", False),
    ("judges[].special[]", "array", "<code>{letters, slugs, title, reason, raw}</code> per “Special elements” bullet; <code>raw</code> is the bullet verbatim.", False),
    ("judges[].files, url", "object, string", "Repo-relative paths of the judge's files; site path of the judge page.", False),
    ("derived.order", "array of slugs", "Candidates by mean rank; candidates not ranked by every judge come after those that were; ties keep the first judge's order.", True),
    ("derived.coverage", "object", "slug → <code>{judges, of}</code>: how many judges ranked the candidate, out of all judges.", True),
    ("derived.mean_rank", "object", "slug → <code>{display, exact, value}</code>: mean of the candidate's ranks over the judges that ranked it — one decimal as in Judge/README.md, an exact fraction, and a number rounded to 4 decimals.", True),
    ("derived.standing", "object", "slug → <code>{place, tied}</code>: competition rank (1, 1, 3, …) by mean rank, among candidates ranked by every judge.", True),
    ("derived.spread", "object", "slug → <code>{min, max, sd}</code>: lowest and highest rank and the population standard deviation (4 decimals).", True),
    ("derived.kendall_tau_b[]", "array", "<code>{a, b, tau, n}</code> per pair of judges: Kendall τ<sub>b</sub> over the n candidates both ranked (4 decimals; null if undefined).", True),
]

CSV_SCHEMA = {
    "ranks.csv": ("One row per judge × ranked candidate, by judge, then rank.", [
        ("judge", "Judge id, e.g. the folder name lowercased without <code>-Judge</code>."),
        ("judge_label", "Readable judge label."),
        ("letter", "The blind letter the judge saw for this candidate."),
        ("slug", "Candidate slug (see results.json <code>candidates[]</code>)."),
        ("folder", "Candidate folder in the repo."),
        ("prompt", "Prompt version (v0/v1) as given in the judge's ranking table."),
        ("rank", "The judge's rank, 1 = best."),
    ]),
    "scores.csv": ("One row per phase-1 review, by review type, then folder.", [
        ("review_type", "Review type id (folder name lowercased without <code>-Review</code>)."),
        ("slug", "Candidate slug."),
        ("folder", "Candidate folder in the repo."),
        ("blind_id", "Phase-1 blind label the reviewer saw."),
        ("overall", "Overall score, 1–10, the first number on the overall-score line (a reviewer's own rounding is not applied)."),
    ]),
    "criteria.csv": ("One row per criterion of every phase-1 review, in the review's table order.", [
        ("review_type", "Review type id."),
        ("slug", "Candidate slug."),
        ("criterion_index", "1-based position of the row in the review's criteria table."),
        ("criterion", "Criterion name as written (leading numbering removed)."),
        ("score", "Score, 1–10."),
        ("reason", "The reviewer's one-line reason, verbatim Markdown."),
    ]),
}


# ---------------------------------------------------------------- git history

def _shallow(repo: str) -> bool:
    try:
        return subprocess.run(["git", "-C", repo, "rev-parse", "--is-shallow-repository"], capture_output=True,
                              text=True, check=True).stdout.strip() == "true"
    except (OSError, subprocess.CalledProcessError):
        return False


def history(site: Site) -> tuple[list[dict], bool]:
    """Commits touching Judge/ and Review/, newest first, each with its added judgments ('entries')
    and its other changed files ('other'). Returns (commits, shallow?)."""
    m = site.model
    try:
        commits = git_history(site.repo, HISTORY_PATHS)
    except (OSError, subprocess.CalledProcessError):
        commits = []
    jorder = {j.folder: i for i, j in enumerate(m.judges)}
    torder = {f: i for i, (_, f, _) in enumerate(m.review_types)}
    out = []
    for cm in commits:
        entries, other = [], []
        for st, path in cm["files"]:
            jm, rm = _JUDGE_RE.match(path), _REVIEW_RE.match(path)
            if st == "A" and (jm or rm):
                e = {"path": path, "sha": cm["sha"], "date": cm["date_iso"], "author": cm["author"]}
                if jm:
                    j = next((x for x in m.judges if x.folder == jm.group(1)), None)
                    label = j.label if j else jm.group(1).removesuffix("-Judge")
                    e.update(kind="judge", obj=j, group="Judge rankings", sort=(0, jorder.get(jm.group(1), 10**6), path),
                             title=f"Added: {label} judge ranking", url=judge_url(j) if j else None,
                             summary=_judge_summary(site, j) if j else f"{path} was added; it is not part of the current build.")
                else:
                    r = next((x for x in m.reviews if x.type_folder == rm.group(1) and x.folder == rm.group(2)), None)
                    if r:
                        title = f"Added: {r.type_label} review of {m.cand(r.slug).label}"
                    else:
                        title = f"Added: {rm.group(1).removesuffix('-Review')} review of {rm.group(2)}"
                    cidx = m.cand(r.slug).index if r else 10**6
                    e.update(kind="review", obj=r, group=f"{r.type_label if r else rm.group(1).removesuffix('-Review')} reviews", sort=(1, torder.get(rm.group(1), 10**6), cidx, path), title=title,
                             url=review_url(r) if r else None,
                             summary=_review_summary(site, r) if r else f"{path} was added; it is not part of the current build.")
                entries.append(e)
            else:
                other.append((st, path))
        entries.sort(key=lambda e: e["sort"])
        out.append({**cm, "entries": entries, "other": other})
    return out, _shallow(site.repo)


def _judge_summary(site: Site, j) -> str:
    m = site.model
    order = "; ".join(f"{x.rank}. {m.cand(x.slug).label} ({x.letter})" for x in j.rows)
    return f"{j.title}. Ranking (1 = best; blind letter in parentheses): {order}."


def _review_summary(site: Site, r) -> str:
    crit = "; ".join(f"{k.name} {fmt_score(k.score)}" for k in r.criteria)
    return f"{r.title}. Overall score: {fmt_score(r.overall)} / 10. Criteria: {crit}."


# ---------------------------------------------------------------- feed.xml

def feed(site: Site, commits: list[dict]) -> str:
    host = urlsplit(site.base_url).hostname or "localhost"
    entries = [e for cm in commits for e in cm["entries"]]
    updated = entries[0]["date"] if entries else site.git["date_iso"]
    author = entries[0]["author"] if entries else (commits[0]["author"] if commits else "MandelbrotXR")
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<feed xmlns="http://www.w3.org/2005/Atom">',
         f"<id>{xesc(site.abs_url(''))}</id>",
         f"<title>{xesc(FEED_TITLE)}</title>",
         "<subtitle>One entry per judge ranking or phase-1 review added to Judge/ or Review/ of "
         "mpuchstein/MandelbrotXR, from the git history.</subtitle>",
         f'<link rel="self" type="application/atom+xml" href="{xesc(site.abs_url("feed.xml"))}"/>',
         f'<link rel="alternate" type="text/html" href="{xesc(site.abs_url("data/changelog/"))}"/>',
         f"<updated>{xesc(updated)}</updated>",
         f"<author><name>{xesc(author)}</name></author>",
         "<generator>MandelbrotXR site/build.py</generator>"]
    for e in entries:
        href = site.abs_url(_url(e["url"])) if e["url"] else f"{GITHUB}/blob/{e['sha']}/{e['path']}"
        L += ["<entry>",
              f"<id>{xesc(f'tag:{host},{e['date'][:10]}:{e['path']}@{e['sha']}')}</id>",
              f"<title>{xesc(e['title'])}</title>",
              f'<link rel="alternate" type="text/html" href="{xesc(href)}"/>',
              f'<link rel="related" type="text/html" href="{xesc(f"{GITHUB}/commit/{e['sha']}")}"/>',
              f"<published>{xesc(e['date'])}</published>",
              f"<updated>{xesc(e['date'])}</updated>",
              f"<author><name>{xesc(e['author'])}</name></author>",
              f'<summary type="text">{xesc(e["summary"])}</summary>',
              "</entry>"]
    L.append("</feed>")
    xml = "\n".join(L) + "\n"
    _validate_feed(xml)
    return xml


def _validate_feed(xml: str) -> None:
    """RFC 4287 required elements: feed id/title/updated (+ author unless every entry has one);
    entry id/title/updated, and a link rel=alternate or content."""
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml.encode("utf-8"))
    assert root.tag == "{http://www.w3.org/2005/Atom}feed", "feed.xml: root is not atom:feed"
    for t in ("id", "title", "updated"):
        assert root.find(f"a:{t}", ns) is not None and (root.find(f"a:{t}", ns).text or "").strip(), f"feed.xml: missing feed {t}"
    has_author = root.find("a:author/a:name", ns) is not None
    ids = set()
    for e in root.findall("a:entry", ns):
        for t in ("id", "title", "updated"):
            assert (e.find(f"a:{t}", ns) is not None) and (e.find(f"a:{t}", ns).text or "").strip(), f"feed.xml: entry lacks {t}"
        assert e.find("a:link[@rel='alternate']", ns) is not None, "feed.xml: entry lacks link rel=alternate"
        assert has_author or e.find("a:author/a:name", ns) is not None, "feed.xml: entry lacks an author"
        i = e.find("a:id", ns).text
        assert i not in ids, f"feed.xml: duplicate entry id {i}"
        ids.add(i)


# ---------------------------------------------------------------- pages

def _pcode(path: str) -> str:
    """<code> for a repo path that breaks only after '/' (segments kept whole), never at a '-' inside a name."""
    return "<code>" + "/<wbr>".join(f'<span class="nw">{esc(seg)}</span>' for seg in path.split("/")) + "</code>"


def _keep(text: str) -> str:
    """Escaped text with ' · v1'-style suffixes bound to the word before them (NBSP), so a version never starts a line."""
    return re.sub(r" · (v\d+)\b", "\u00a0·\u00a0\\1", esc(text))


def _date(iso: str) -> str:
    return f'<time datetime="{esc(iso)}">{esc(iso[:10])}</time>'


def changelog_page(site: Site, commits: list[dict], shallow: bool) -> None:
    n_entries = sum(len(c["entries"]) for c in commits)
    n_with = sum(1 for c in commits if c["entries"])
    parts = ['<header class="data-head"><h1>Changelog</h1>'
             '<p class="lede">Every judgment added to the repository, newest first: one entry per judge ranking '
             '(each judge\'s <code>RANKING.md</code>) or phase-1 review (each review\'s <code>REVIEW.md</code>), '
             'grouped under the commit that added it. Generated from the git history of <code>Judge/</code> and <code>Review/</code>.</p>'
             f'<p class="data-links"><a class="btn" href="@/feed.xml">Atom feed</a> <a class="btn" href="@/data/">Data &amp; schema</a></p></header>']
    if shallow:
        parts.append('<p class="note">This build ran on a shallow clone; the history below may be incomplete.</p>')
    if not commits:
        parts.append('<p class="note">No git history of <code>Judge/</code> or <code>Review/</code> was available to this build, '
                     'so there are no entries.</p>')
    else:
        parts.append(f'<p class="muted small">{n_entries} added judgment{"s" if n_entries != 1 else ""} in {n_with} '
                     f'commit{"s" if n_with != 1 else ""}; {len(commits)} commit{"s" if len(commits) != 1 else ""} touched these folders in total.</p>')
    parts.append('<ol class="changelog">')
    for cm in commits:
        sha = cm["sha"]
        # meta items wrap as whole units; the '·' separator is drawn before each item after the first (data.css)
        head = (f'<div class="cl-meta"><span class="cl-mi">{_date(cm["date_iso"])}</span> <span class="cl-mi"><a href="{GITHUB}/commit/{sha}" rel="noopener"><code>{sha[:7]}</code></a></span>'
                f' <span class="cl-mi">{esc(cm["author"])}</span></div><h2 class="cl-subject" id="c-{sha[:12]}">{esc(cm["subject"])}</h2>')
        groups_e: dict[str, list[str]] = {}
        for e in cm["entries"]:
            label = _keep(e["title"].removeprefix("Added: "))
            link = f'<a href="{esc(e["url"])}">{label}</a>' if e["url"] else f'{label} <span class="muted">(not in this build)</span>'
            extra = ""
            if e["kind"] == "review" and e["obj"]:
                extra = (f'<span class="cl-mid cl-score num"><span class="sr-only">overall score </span>{esc(fmt_score(e["obj"].overall))}'
                         f'<span class="muted">/10</span></span>')
            elif e["kind"] == "judge" and e["obj"] and e["obj"].rows:
                top = site.model.cand(e["obj"].rows[0].slug)
                extra = f'<span class="cl-mid cl-top"><span class="muted">ranked first:</span> {_keep(top.label)}</span>'
            src = (f'<span class="cl-src small"><a href="{GITHUB}/blob/{sha}/{esc(e["path"])}" rel="noopener" '
                   f'title="{esc(e["path"])} as added in {sha[:7]}">GitHub<span class="sr-only">: {esc(e["path"])}</span> '
                   f'<span aria-hidden="true">↗</span></a></span>')
            groups_e.setdefault(e["group"], []).append(f'<li><span class="cl-what">{link}</span>{extra}{src}</li>')
        body = "".join(f'<h3 class="cl-group">{esc(g)} <span class="muted num">({len(v)})</span></h3><ul class="cl-entries">{"".join(v)}</ul>'
                       for g, v in groups_e.items())
        if not body:
            body = '<p class="muted small">No judgments added in this commit.</p>'
        other = ""
        if cm["other"]:
            groups: dict[str, list[tuple[str, str]]] = {}
            for st, p in cm["other"]:
                groups.setdefault(os.path.dirname(p), []).append((st, os.path.basename(p)))
            word = {"A": "added", "M": "modified", "D": "deleted", "T": "type changed"}
            rows = []
            for d in sorted(groups):
                bys: dict[str, list[str]] = {}
                for st, n in groups[d]:
                    bys.setdefault(word.get(st[:1], st), []).append(n)
                desc = "; ".join(f"{k}: {', '.join(esc(x) for x in v)}" for k, v in bys.items())
                rows.append(f'<li><code>{esc(d)}/</code> — {desc}</li>')
            n = len(cm["other"])
            other = (f'<details class="fold cl-other"><summary>{n} other file{"s" if n != 1 else ""} changed in '
                     f'{len(groups)} folder{"s" if len(groups) != 1 else ""}</summary><ul>{"".join(rows)}</ul></details>')
        parts.append(f'<li class="cl-commit">{head}{body}{other}</li>')
    parts.append('</ol>')
    body = "\n".join(parts)
    site.page("data/changelog/index.html", "Changelog", body, section="data",
              crumbs=[("Data", "data/"), ("Changelog", "")],
              description="Every judge ranking and review added to the MandelbrotXR repository, from the git history; also as an Atom feed.")
    site.search_doc("data/changelog/", "Changelog", "page", "Data · changes",
                    " ".join(f'{cm["subject"]}. ' + " ".join(e["title"] for e in cm["entries"]) for cm in commits))


_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")


def _word(n: int) -> str:
    """A count for prose: spelled out up to twelve, digits above (always derived, never hardcoded)."""
    return _WORDS[n] if 0 <= n < len(_WORDS) else str(n)


def data_page(site: Site, files: dict[str, bytes], commits: list[dict]) -> None:
    m, g = site.model, site.git
    tree = f"{GITHUB}/tree/{g['sha']}"
    tag = '<span class="derived">derived</span>'
    desc = {
        "results.json": "Everything in one file: candidates, reviews with criteria, judge rankings with verbatim justifications and special elements, and the derived metrics.",
        "ranks.csv": CSV_SCHEMA["ranks.csv"][0],
        "scores.csv": CSV_SCHEMA["scores.csv"][0],
        "criteria.csv": CSV_SCHEMA["criteria.csv"][0],
    }
    def rows_of(name: str) -> str:
        b = files[name]
        if name.endswith(".csv"):
            n = b.decode("utf-8").count("\n") - 1
            return f"{n} rows"
        return f"{len(m.candidates)} candidates · {len(m.reviews)} reviews · {len(m.judges)} judges"
    flist = "".join(
        f'<li class="card data-file"><a class="data-file-name" href="@/data/{n}" download><code>{esc(n)}</code></a>'
        f'<p class="data-file-meta small muted num">{"JSON" if n.endswith(".json") else "CSV"} · {esc(_size(len(files[n])))}'
        f'<br>{esc(rows_of(n))}</p>'
        f'<p class="data-file-desc">{esc(desc[n])}</p></li>' for n in files)
    rs = "".join(
        f'<tr><th scope="row"><code>{esc(f).replace(".", "<wbr>.")}</code><span class="schema-type">{esc(t)}</span></th><td>{mean}{(" " + tag) if d else ""}</td></tr>'
        for f, t, mean, d in RESULTS_SCHEMA)
    csv_secs = []
    for name, (what, cols) in CSV_SCHEMA.items():
        crow = "".join(f'<tr><th scope="row"><code>{esc(c)}</code></th><td>{mean}</td></tr>' for c, mean in cols)
        head_line = files[name].decode("utf-8").split("\n", 1)[0]
        csv_secs.append(
            f'<h3 id="{esc(name.replace(".", "-"))}"><code>{esc(name)}</code></h3><p>{esc(what)} Header row: <code>{esc(head_line)}</code>.</p>'
            f'<div class="table-wrap"><table class="schema"><caption class="sr-only">Columns of {esc(name)}</caption>'
            f'<thead><tr><th scope="col">Column</th><th scope="col">Meaning</th></tr></thead><tbody>{crow}</tbody></table></div>')
    c0 = json.loads(files["results.json"])["candidates"][:1]
    sample = json.dumps(c0[0], indent=1, ensure_ascii=False) if c0 else "{}"
    recent = []
    for cm in commits:
        for e in cm["entries"]:
            recent.append(e)
    rec_html = ""
    if recent:
        latest = recent[0]["date"]
        same = [e for e in recent if e["date"] == latest]
        rec_html = (f'<p>Latest: {len(same)} judgment{"s" if len(same) != 1 else ""} added on {_date(latest)}. '
                    f'{len(recent)} in total since the first commit.</p>')
    body = f"""<header class="data-head"><h1>Data</h1>
<p class="lede">The complete results as machine-readable files: one JSON export with everything and {_word(sum(1 for n in files if n.endswith(".csv")))} flat CSV tables.
They are generated from the repository at commit <a href="{GITHUB}/commit/{g['sha']}" rel="noopener"><code>{esc(g['version'][:12])}</code></a>
({_date(g['date_iso'])}) by the same build that writes this site, so every number here equals the one on the pages.</p></header>
<section class="data-sec" aria-labelledby="files"><h2 id="files">Files</h2>
<ul class="data-file-list">{flist}</ul>
<p class="small muted">UTF-8, <code>\\n</code> line endings. CSVs have a header row and RFC 4180 quoting; JSON keys keep the order documented below.
Two builds of the same commit produce byte-identical files.</p>
</section>
<section class="data-sec" aria-labelledby="provenance"><h2 id="provenance">Provenance and licence</h2>
<ul class="data-notes">
<li>Source: the committed files of <a href="{tree}" rel="noopener">mpuchstein/MandelbrotXR at <code>{esc(g['sha'][:7])}</code></a>:
<ul class="data-paths">
<li>{_pcode("site/candidates.toml")}: the candidate list (the only file entered by hand)</li>
<li>{_pcode("Review/*-Review/*/REVIEW.md")}: every phase-1 review</li>
<li>{_pcode("Judge/*-Judge/RANKING.md")}: every judge ranking</li>
<li>{_pcode("Judge/judge-mapping.json")}: the judges' letter mapping</li>
<li>{_pcode("ReviewOrchestrator/blind-mapping.json")}: the reviewers' blind ids</li>
<li>{_pcode("ReviewOrchestrator/blind/source-html.sha256")}: checksums of the blinded HTML copies</li>
</ul></li>
<li>Verdicts are verbatim: justifications, reasons and special-element bullets are the judges' and reviewers' Markdown, unchanged. Scores and ranks are parsed, not edited.</li>
<li>Fields marked {tag} are computed by the build; see <a href="#derived-fields">Derived fields</a> and <a href="@/methodology/#derived">Methodology</a>.</li>
<li>The repository has no licence file at this commit; reuse terms are the repository owner's.</li>
</ul></section>
<section class="data-sec" aria-labelledby="results-schema"><h2 id="results-schema"><code>results.json</code> schema</h2>
<p>A single object. Paths are repository-relative; <code>urls</code> and <code>url</code> fields are site paths relative to the site root.
Integers stay integers; other numbers are rounded to {DEC} decimals.</p>
<div class="table-wrap"><table class="schema"><caption class="sr-only">Fields of results.json</caption>
<thead><tr><th scope="col">Field and type</th><th scope="col">Meaning</th></tr></thead><tbody>{rs}</tbody></table></div>
<details class="fold"><summary>Example: the first <code>candidates[]</code> object</summary><pre tabindex="0" aria-label="Example candidate object (JSON)"><code>{esc(sample)}</code></pre></details>
</section>
<section class="data-sec" aria-labelledby="csv-schema"><h2 id="csv-schema">CSV columns</h2>
{''.join(csv_secs)}
</section>
<section class="data-sec" aria-labelledby="derived-fields"><h2 id="derived-fields">Derived fields {tag}</h2>
<p>The judges produced ranks and the reviewers produced scores; everything under <code>derived</code> is computed by this site from those numbers:</p>
<ul class="data-notes">
<li><strong>Mean rank</strong> = sum of a candidate's ranks ÷ number of judges that ranked it. <code>display</code> rounds to one decimal, as in <code>Judge/README.md</code>;
<code>exact</code> is the fraction, so ties are exact (equal fractions = tie).</li>
<li><strong>Standing</strong>: competition rank by mean rank (1, 1, 3, …) among candidates ranked by every judge; <code>tied</code> marks shared places.</li>
<li><strong>Spread</strong>: min and max rank, and σ = √(Σ(r − mean)² / n), the population standard deviation.</li>
<li><strong>Kendall τ<sub>b</sub></strong> between two judges over the candidates both ranked: (C − D) / √((C + D + T<sub>a</sub>)(C + D + T<sub>b</sub>)).</li>
<li><strong><code>external</code> and <code>alert_calls</code></strong> come from scanning each product file for absolute resource URLs and <code>alert(</code> calls.</li>
</ul></section>
<section class="data-sec" aria-labelledby="changes"><h2 id="changes">Changes</h2>
{rec_html}
<p>The <a href="@/data/changelog/">Changelog</a> lists every judge ranking and review added to the repository, from its git history;
<a href="@/feed.xml">feed.xml</a> carries the same entries as an Atom feed.</p>
</section>"""
    site.page("data/index.html", "Data", body, section="data", crumbs=[("Data", "")],
              description="MandelbrotXR results as JSON and CSV, with a documented schema, provenance, a changelog and an Atom feed.")
    site.search_doc("data/", "Data and schema", "page", "Data · results.json, CSV",
                    _plain(html.unescape(re.sub(r"<[^>]+>", " ", body))))


def build(site: Site) -> None:
    res = results(site)
    files = {"results.json": (json.dumps(res, indent=1, ensure_ascii=False) + "\n").encode("utf-8")}
    files.update({k: v.encode("utf-8") for k, v in csvs(site).items()})
    for name, b in files.items():
        site.write(f"data/{name}", b)
    commits, shallow = history(site)
    site.write("feed.xml", feed(site, commits).encode("utf-8"))
    data_page(site, files, commits)
    changelog_page(site, commits, shallow)
