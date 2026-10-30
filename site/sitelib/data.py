"""Load, parse and validate every data source of the MandelbrotXR results site.

Everything is discovered from the repository (see site/BRIEF.md, "Extensibility"):
- candidates: site/candidates.toml (the only hand-edited file)
- judges: every Judge/*-Judge/ folder with a RANKING.md and an entry in Judge/judge-mapping.json
- review types: every Review/*-Review/ folder
Inconsistent data raises DataError naming the offending file; nothing is skipped silently.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations

from . import img


class DataError(Exception):
    """Inconsistent or unparsable source data. The message names the file."""


def fail(path: str, msg: str) -> None:
    raise DataError(f"{path}: {msg}")


# ---------------------------------------------------------------- model

CAND_FIELDS = ("slug", "folder", "name", "label", "vendor", "product", "model", "effort", "provenance",
               "prompt", "product_file", "source_url", "date")
CAND_OPTIONAL = ("thumbnail",)


@dataclass
class Shot:
    """One screenshot, attributed to a candidate and to the review or judge that took it."""
    path: str            # repo-relative
    source: str          # "review" | "judge" | "discarded"
    source_id: str       # review key ("browser/<slug>") or judge id
    source_label: str
    slug: str | None     # candidate slug (None if unattributed)
    width: int
    height: int
    caption: str | None  # verbatim line of the review/ranking that mentions the file, if any


@dataclass
class Candidate:
    slug: str
    folder: str
    name: str
    label: str
    vendor: str
    product: str
    model: str
    effort: str
    provenance: str
    prompt: str
    product_file: str
    source_url: str
    date: str
    index: int                       # position in candidates.toml (stable colour index)
    html_path: str = ""              # repo-relative product path
    bytes: int = 0
    sha256: str = ""
    external: list[str] = field(default_factory=list)   # absolute URLs loaded by the product
    alert_calls: int = 0
    transcription: str = ""          # repo-relative TRANSCRIPTION.md
    shots: list[Shot] = field(default_factory=list)
    thumbnail_path: str = ""         # candidates.toml `thumbnail` (repo-relative), validated against shots

    @property
    def thumbnail(self) -> Shot | None:
        if self.thumbnail_path:
            return next(s for s in self.shots if s.path == self.thumbnail_path)
        for kind in ("review", "judge"):
            for s in self.shots:
                if s.source == kind:
                    return s
        return None


@dataclass
class Criterion:
    name: str
    score: float
    reason: str


@dataclass
class Review:
    type_id: str          # "html", "transcript", "browser", ...
    type_folder: str      # "HTML-Review"
    type_label: str       # "HTML"
    slug: str
    folder: str
    blind_id: str         # "candidate-05"
    title: str            # H1 as written
    overall: float
    overall_line: str     # verbatim source line the score was parsed from
    criteria: list[Criterion]
    md: str
    dir: str              # repo-relative review folder
    files: dict[str, str] # name -> repo-relative path (PROMPT.txt, REVIEW.md, TRANSCRIPT.md)
    shots: list[Shot] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.type_id}/{self.slug}"


@dataclass
class RankRow:
    rank: int
    letter: str
    slug: str
    prompt: str
    justification: str    # verbatim Markdown cell


@dataclass
class Special:
    letters: list[str]
    slugs: list[str]
    title: str            # the bold label without the letters
    reason: str           # the sentence after the label (Markdown)
    raw: str              # the full bullet, verbatim


@dataclass
class Judge:
    id: str               # "html_transcript"
    folder: str           # "HTML_TRANSCRIPT-Judge"
    label: str            # "HTML + Transcript"
    title: str            # RANKING.md H1
    material: str | None  # from Judge/README.md "Judges" table
    focus: str | None
    browser: bool         # hands-on in a browser (vs static material only)
    mapping: dict[str, str]          # letter -> slug
    letter_prompt: dict[str, str]
    alerts_patched: dict[str, int]
    rows: list[RankRow]
    criteria_md: str
    special: list[Special]
    summary_md: str
    md: str
    dir: str
    files: dict[str, str]
    shots: list[Shot] = field(default_factory=list)

    @property
    def rank(self) -> dict[str, int]:
        return {r.slug: r.rank for r in self.rows}


@dataclass
class Model:
    repo: str
    candidates: list[Candidate]
    judges: list[Judge]
    review_types: list[tuple[str, str, str]]   # (type_id, folder, label)
    reviews: list[Review]
    blind: dict[str, str]                       # candidate-NN -> slug
    discarded: list[dict]                       # discarded runs (path, files, shots)
    sha_file: str

    # ---- lookups
    def cand(self, slug: str) -> Candidate:
        return self._by_slug[slug]

    def review(self, type_id: str, slug: str) -> Review | None:
        return self._reviews.get((type_id, slug))

    def judge(self, jid: str) -> Judge:
        return next(j for j in self.judges if j.id == jid)

    def __post_init__(self) -> None:
        self._by_slug = {c.slug: c for c in self.candidates}
        self._reviews = {(r.type_id, r.slug): r for r in self.reviews}

    # ---- derived metrics (documented on the rankings page)
    def ranks(self, slug: str) -> dict[str, int]:
        """judge id -> rank, only for judges that ranked this candidate."""
        return {j.id: j.rank[slug] for j in self.judges if slug in j.rank}

    def mean_rank(self, slug: str) -> Fraction | None:
        r = list(self.ranks(slug).values())
        return Fraction(sum(r), len(r)) if r else None

    def spread(self, slug: str) -> tuple[int, int, float] | None:
        """(min, max, population standard deviation) of a candidate's ranks."""
        r = list(self.ranks(slug).values())
        if not r:
            return None
        mu = sum(r) / len(r)
        return min(r), max(r), math.sqrt(sum((x - mu) ** 2 for x in r) / len(r))

    def coverage(self, slug: str) -> tuple[int, int]:
        """(judges that ranked this candidate, total judges)."""
        return len(self.ranks(slug)), len(self.judges)

    def full(self, slug: str) -> bool:
        """Ranked by every judge (only then is its mean rank comparable to the others')."""
        n, total = self.coverage(slug)
        return total > 0 and n == total

    def ordered(self) -> list[Candidate]:
        """Candidates by mean rank. Candidates not ranked by every judge come after those that
        were (their means are not comparable), unranked ones last. Ties keep the order of the
        first judge's ranking, then candidates.toml order — the order Judge/README.md shows."""
        first = self.judges[0].rank if self.judges else {}
        def key(c: Candidate):
            m = self.mean_rank(c.slug)
            return (m is None, not self.full(c.slug), m or 0, first.get(c.slug, 10**6), c.index)
        return sorted(self.candidates, key=key)

    def standing(self) -> dict[str, tuple[int, bool]]:
        """slug -> (competition rank by mean rank, tied?), among candidates ranked by every judge."""
        means = {c.slug: self.mean_rank(c.slug) for c in self.candidates if self.full(c.slug)}
        vals = list(means.values())
        return {s: (1 + sum(1 for v in vals if v < m), sum(1 for v in vals if v == m) > 1) for s, m in means.items()}

    def kendall(self, a: Judge, b: Judge) -> tuple[float | None, int]:
        """Kendall tau-b between two judges over the candidates both ranked, and that count."""
        common = sorted(set(a.rank) & set(b.rank))
        conc = disc = ta = tb = 0
        for x, y in combinations(common, 2):
            da = a.rank[x] - a.rank[y]
            db = b.rank[x] - b.rank[y]
            if da == 0 and db == 0:
                continue
            if da == 0:
                ta += 1
            elif db == 0:
                tb += 1
            elif (da > 0) == (db > 0):
                conc += 1
            else:
                disc += 1
        denom = math.sqrt((conc + disc + ta) * (conc + disc + tb))
        return ((conc - disc) / denom if denom else None), len(common)

    def kendall_pairs(self) -> list[tuple[Judge, Judge, float | None, int]]:
        return [(a, b, *self.kendall(a, b)) for a, b in combinations(self.judges, 2)]

    def rank_table_md(self) -> str:
        """The aggregated rank table in exactly the format of Judge/README.md."""
        js = self.judges
        lines = ["| Folder | Prompt | " + " | ".join(j.folder.removesuffix("-Judge") for j in js) + " | Mean |",
                 "|---|---|" + "---|" * len(js) + "---|"]
        for c in self.ordered():
            r = self.ranks(c.slug)
            if not r:
                continue
            cells = " | ".join(str(r[j.id]) if j.id in r else "–" for j in js)
            lines.append(f"| `{c.folder}` | {c.prompt} | {cells} | {fmt_mean(self.mean_rank(c.slug))} |")
        return "\n".join(lines)


def fmt_mean(m: Fraction | None) -> str:
    return "–" if m is None else f"{float(m):.1f}"


def fmt_score(x: float) -> str:
    return f"{x:g}"


def label_of(type_id: str) -> str:
    """'html_transcript' -> 'HTML + Transcript', 'browser' -> 'Browser'."""
    return " + ".join("HTML" if p == "html" else p.capitalize() for p in type_id.split("_"))


# ---------------------------------------------------------------- helpers

def _read(repo: str, rel: str) -> str:
    try:
        with open(os.path.join(repo, rel), encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise DataError(f"{rel}: cannot read ({e.strerror})") from None


def _json(repo: str, rel: str):
    try:
        return json.loads(_read(repo, rel))
    except json.JSONDecodeError as e:
        raise DataError(f"{rel}: invalid JSON ({e})") from None


_FILES: dict[str, frozenset] = {}


def repo_files(repo: str) -> frozenset:
    """Repo-relative paths git considers part of the tree: committed plus untracked-but-not-ignored files
    (the latter mark the build '-dirty'). Ignored files (caches, build output) are never rendered."""
    if repo not in _FILES:
        out = git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
        _FILES[repo] = frozenset(p for p in out.split("\0") if p and os.path.exists(os.path.join(repo, p)))
    return _FILES[repo]


def _listdir(repo: str, rel: str) -> list[str]:
    """Entries of a repo directory that contain (or are) files known to git; see repo_files()."""
    prefix = rel.rstrip("/") + "/"
    names = {p[len(prefix):].split("/", 1)[0] for p in repo_files(repo) if p.startswith(prefix)}
    return sorted(n for n in names if n != "__pycache__" and not n.startswith("."))


def section(md: str, heading: str) -> str | None:
    """Body of the '## heading' section (up to the next '## '), or None."""
    m = re.search(rf"^## {re.escape(heading)}[ \t]*$", md, re.M)
    if not m:
        return None
    rest = md[m.end():]
    n = re.search(r"^## ", rest, re.M)
    return (rest[:n.start()] if n else rest).strip("\n")


def table_rows(block: str) -> tuple[list[str], list[list[str]]]:
    """(header cells, body rows) of the first GFM table in block. Escaped pipes are kept."""
    lines = []
    for l in block.splitlines():
        if l.strip().startswith("|"):
            lines.append(l)
        elif lines:
            break
    if len(lines) < 2:
        return [], []
    split = lambda l: [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", l.strip())[1:-1]]
    head = split(lines[0])
    body = [split(l) for l in lines[1:] if not re.match(r"^\|\s*:?-", l.strip())]
    return head, body


def _num(s: str) -> float | None:
    m = re.search(r"\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def _plain(s: str) -> str:
    """Cell text without emphasis markers and backticks (underscores inside words are kept)."""
    return re.sub(r"\*\*|(?<![A-Za-z0-9])__|__(?![A-Za-z0-9])|`", "", s).strip()


# ---------------------------------------------------------------- parsers

_SCALE = re.compile(r"\(\s*(?:\d+\s*[–-]\s*\d+|out of \d+)\s*\)", re.I)


def parse_overall(md: str, path: str) -> tuple[float, str]:
    """First number of the overall-score line. Tolerates every format in the repo:
    'Overall score: **4 / 10**', '8 / 10**', '5/10', '2.5 / 10 (rounded: 3)', '| **Overall** | **7** |',
    and skips a scale such as the review prompts' own label '**Overall score (1–10)**'."""
    for line in md.splitlines():
        if re.search(r"overall score", line, re.I):
            tail = re.split(r"overall score", line, flags=re.I)[1]
            n = _num(_SCALE.sub("", tail))
            if n is not None:
                return n, line.strip()
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
        if len(cells) >= 2 and _plain(cells[0]).lower() == "overall":
            n = _num(cells[1])
            if n is not None:
                return n, line.strip()
    fail(path, "no parsable overall score (expected an 'Overall score: N / 10' line or an '| Overall | N |' row)")


def parse_criteria(md: str, path: str) -> list[Criterion]:
    head, rows = table_rows(md)
    if not head or "criterion" not in head[0].lower():
        fail(path, "no criteria table (first table must have a 'Criterion' column)")
    out = []
    for r in rows:
        if len(r) < 3:
            fail(path, f"criteria row has {len(r)} cells: {r}")
        name = _plain(r[0])
        if name.lower() == "overall":
            continue
        score = _num(_plain(r[1]))
        if score is None:
            fail(path, f"unparsable criterion score {r[1]!r} for {name!r}")
        out.append(Criterion(re.sub(r"^\d+\.\s*", "", name), score, r[2]))
    if not out:
        fail(path, "criteria table is empty")
    return out


def parse_ranking(md: str, path: str, letters: set[str]) -> list[tuple[int, str, str, str]]:
    """(rank, letter, prompt, justification) rows of the '## Ranking' table, in table order.
    Generalises judge_finalize.check_ranking to any letter set."""
    for h in ("Ranking criteria", "Ranking", "Special elements", "Summary of tests and approach"):
        if section(md, h) is None:
            fail(path, f"missing section '## {h}'")
    head, rows = table_rows(section(md, "Ranking"))
    cols = {h.lower(): i for i, h in enumerate(head)}
    need = ("rank", "candidate", "prompt", "justification")
    if any(k not in cols for k in need):
        fail(path, f"ranking table needs columns {need}, has {head}")
    out = []
    for pos, r in enumerate(rows, 1):
        cell = _plain(r[cols["candidate"]])
        m = re.fullmatch(r"([A-Z])", cell)
        if not m:
            fail(path, f"ranking row {pos}: candidate cell {cell!r} is not a single letter")
        rank = _num(r[cols["rank"]])
        if rank != pos:
            fail(path, f"ranking row {pos}: rank cell {r[cols['rank']]!r} does not match its position")
        out.append((pos, m.group(1), _plain(r[cols["prompt"]]), r[cols["justification"]]))
    got = [o[1] for o in out]
    if len(set(got)) != len(got):
        fail(path, f"a letter appears twice in the ranking: {got}")
    missing = sorted(set(got) - letters)
    if missing:
        fail(path, f"letter(s) {missing} ranked but missing from Judge/judge-mapping.json")
    unranked = sorted(letters - set(got))
    if unranked:
        fail(path, f"mapping letter(s) {unranked} not ranked")
    return out


_SPECIAL = re.compile(r"^\s*[-*]\s+\*\*(?P<bold>.+?)\*\*(?P<rest>.*)$")
_LETTERS = re.compile(r"^(?P<ls>[A-Z](?![A-Za-z0-9])(?:\s*(?:,|&|\band\b)\s*[A-Z](?![A-Za-z0-9]))*)\s*(?:—|–|-|,|:)\s*(?P<title>.*)$")


def parse_special(md: str, path: str, mapping: dict[str, str]) -> list[Special]:
    body = section(md, "Special elements") or ""
    items, cur = [], None
    for line in body.splitlines():
        if re.match(r"^\s*[-*]\s+", line):
            cur = [line]
            items.append(cur)
        elif cur is not None and line.strip():
            cur.append(line.strip())
    out = []
    for item in items:
        raw = " ".join(s.strip() for s in item)
        m = _SPECIAL.match(raw)
        lm = _LETTERS.match(m.group("bold").strip()) if m else None
        if not lm:
            fail(path, f"unparsable special-elements bullet (expected '- **<letters> — <element>**: <reason>'): {raw[:120]!r}")
        letters = re.findall(r"[A-Z](?![A-Za-z0-9])", lm.group("ls"))
        for l in letters:
            if l not in mapping:
                fail(path, f"special element names letter {l!r}, which is missing from Judge/judge-mapping.json")
        title = lm.group("title").strip().rstrip(":").strip()
        rest = m.group("rest").strip()
        closed = m.group("bold").rstrip().endswith(":")     # '**H — x:** reason': the title ends inside the bold
        if not closed and not rest.startswith(":") and ": " in rest:  # '**H — x** (details): reason', '**H — x** for y: reason'
            extra, rest = rest.split(": ", 1)
            title = f"{title} {extra.strip()}"
        rest = rest.lstrip(":").strip()
        out.append(Special(letters, [mapping[l] for l in letters], title, rest, re.sub(r"^\s*[-*]\s+", "", raw)))
    return out


def _judges_table(repo: str) -> dict[str, tuple[str, str]]:
    """Judge/README.md 'Judges' table: folder -> (material, special-elements focus)."""
    p = "Judge/README.md"
    if not os.path.exists(os.path.join(repo, p)):
        return {}
    sec = section(_read(repo, p), "Judges") or ""
    head, rows = table_rows(sec)
    out = {}
    for r in rows:
        if len(r) >= 3:
            out[_plain(r[0]).strip("/")] = (r[1], r[2])
    return out


def _caption(md: str, filename: str) -> str | None:
    for line in md.splitlines():
        if filename in line:
            return line.strip()
    stem = os.path.splitext(filename)[0]
    for line in md.splitlines():
        if stem in line:
            return line.strip()
    return None


# ---------------------------------------------------------------- products

_EXT = re.compile(r"""<(?:script|link|img|iframe|source|video|audio)\b[^>]*?\s(?:src|href)\s*=\s*["'](https?://[^"']+)["']""", re.I)
_CSS_EXT = re.compile(r"""@import\s+(?:url\()?\s*["']?(https?://[^"')\s]+)""", re.I)
_ALERT = re.compile(r"(?<![\w.$])(?:window\.)?alert\s*\(")


def product_facts(data: bytes) -> tuple[list[str], int]:
    """(absolute URLs the page loads as resources, number of alert( calls)."""
    text = data.decode("utf-8", "replace")
    ext = []
    for m in list(_EXT.finditer(text)) + list(_CSS_EXT.finditer(text)):
        tag = text[m.start():m.end()]
        if re.match(r"<link\b", tag, re.I) and re.search(r"""rel\s*=\s*["']?(?:preconnect|dns-prefetch|canonical|alternate|icon)""", tag, re.I):
            continue
        if m.group(1) not in ext:
            ext.append(m.group(1))
    return ext, len(_ALERT.findall(text))


# ---------------------------------------------------------------- git

def git(repo: str, *args: str) -> str:
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True).stdout


def git_info(repo: str) -> dict:
    """Commit SHA (+ '-dirty'), commit date and shallow handling. Never uses the wall clock."""
    if git(repo, "rev-parse", "--is-shallow-repository").strip() == "true":
        subprocess.run(["git", "-C", repo, "fetch", "--unshallow"], check=True)
    sha = git(repo, "rev-parse", "HEAD").strip()
    dirty = bool(git(repo, "status", "--porcelain").strip())
    iso = git(repo, "log", "-1", "--format=%cI", "HEAD").strip()
    return {"sha": sha, "dirty": dirty, "version": sha + ("-dirty" if dirty else ""), "date_iso": iso, "date": iso[:10]}


def git_history(repo: str, paths: list[str]) -> list[dict]:
    """Commits touching paths, newest first: sha, date, subject, author, added/modified files."""
    out = git(repo, "log", "--format=\x1e%H\x1f%cI\x1f%an\x1f%s", "--name-status", "--no-renames", "--", *paths)
    commits = []
    for chunk in out.split("\x1e")[1:]:
        head, _, body = chunk.partition("\n")
        sha, iso, author, subject = head.split("\x1f")
        files = []
        for line in body.splitlines():
            if line.strip():
                st, _, p = line.partition("\t")
                files.append((st.strip(), p.strip()))
        commits.append({"sha": sha, "date_iso": iso, "author": author, "subject": subject, "files": files})
    return commits


# ---------------------------------------------------------------- loader

def load(repo: str) -> Model:
    repo = os.path.abspath(repo)
    _FILES.pop(repo, None)  # re-read the file list on every load (tests mutate repos between loads)
    cpath = "site/candidates.toml"
    try:
        raw = tomllib.loads(_read(repo, cpath)).get("candidate", [])
    except tomllib.TOMLDecodeError as e:
        raise DataError(f"{cpath}: invalid TOML ({e})") from None
    cands: list[Candidate] = []
    for i, c in enumerate(raw):
        missing = [k for k in CAND_FIELDS if not isinstance(c.get(k), str) or not c.get(k)]
        if missing:
            fail(cpath, f"candidate #{i + 1} lacks field(s) {missing}")
        unknown = sorted(set(c) - set(CAND_FIELDS) - set(CAND_OPTIONAL))
        if unknown:
            fail(cpath, f"candidate {c['slug']!r} has unknown field(s) {unknown}")
        if not isinstance(c.get("thumbnail", ""), str):
            fail(cpath, f"candidate {c['slug']!r}: thumbnail must be a string (a repo-relative screenshot path)")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", c["slug"]):
            fail(cpath, f"slug {c['slug']!r} must be lowercase a-z0-9 words joined by '-'")
        if c["prompt"] not in ("v0", "v1") and not os.path.exists(os.path.join(repo, f"prompt{c['prompt'][1:]}.txt")):
            fail(cpath, f"candidate {c['slug']!r}: prompt {c['prompt']!r} has no prompt{c['prompt'][1:]}.txt")
        cands.append(Candidate(**{k: c[k] for k in CAND_FIELDS}, index=i, thumbnail_path=c.get("thumbnail", "")))
    for key in ("slug", "folder"):
        seen = [getattr(c, key) for c in cands]
        dup = sorted({s for s in seen if seen.count(s) > 1})
        if dup:
            fail(cpath, f"duplicate {key}(s) {dup}")
    by_folder = {c.folder: c for c in cands}

    # products + integrity
    sha_file = "ReviewOrchestrator/blind/source-html.sha256"
    expected = {}
    for line in _read(repo, sha_file).splitlines():
        if line.strip():
            h, _, p = line.partition("  ")
            expected[p.strip()] = h.strip()
    for c in cands:
        c.html_path = f"{c.folder}/{c.product_file}"
        full = os.path.join(repo, c.html_path)
        if not os.path.isfile(full):
            fail(cpath, f"candidate {c.slug!r}: product file {c.html_path} does not exist")
        data = open(full, "rb").read()
        c.bytes, c.sha256 = len(data), hashlib.sha256(data).hexdigest()
        if c.html_path not in expected:
            fail(sha_file, f"no checksum for {c.html_path}")
        if expected[c.html_path] != c.sha256:
            fail(sha_file, f"sha256 mismatch for {c.html_path}: file is {c.sha256}, list says {expected[c.html_path]}")
        c.external, c.alert_calls = product_facts(data)
        c.transcription = f"{c.folder}/TRANSCRIPTION.md"
        if not os.path.isfile(os.path.join(repo, c.transcription)):
            fail(cpath, f"candidate {c.slug!r}: {c.transcription} does not exist")
        src = re.search(r"^- Source:\s*(\S+)", _read(repo, c.transcription), re.M)
        if src and src.group(1) != c.source_url:
            fail(cpath, f"candidate {c.slug!r}: source_url {c.source_url} differs from the '- Source:' line of {c.transcription} ({src.group(1)})")

    # phase-1 blinding
    bpath = "ReviewOrchestrator/blind-mapping.json"
    blind = {}
    for nn, v in sorted(_json(repo, bpath).items()):
        if v.get("name") not in by_folder:
            fail(bpath, f"{nn} maps to {v.get('name')!r}, which is not in {cpath}")
        other = next((k for k, s in blind.items() if s == by_folder[v["name"]].slug), None)
        if other:
            fail(bpath, f"{other} and {nn} both map to {v['name']!r}")
        blind[nn] = by_folder[v["name"]].slug
    unblind = {s: nn for nn, s in blind.items()}

    # review types (order: ReviewOrchestrator/README.md §4 columns, then alphabetical)
    folders = [d for d in _listdir(repo, "Review") if d.endswith("-Review") and os.path.isdir(os.path.join(repo, "Review", d))]
    order = []
    readme = os.path.join(repo, "ReviewOrchestrator/README.md")
    if os.path.exists(readme):
        head, _ = table_rows(section(open(readme, encoding="utf-8").read(), "4. Results: overall scores (1–10)") or "")
        order = [h.lower() for h in head[1:]]
    tid = lambda d: d.removesuffix("-Review").lower()
    folders.sort(key=lambda d: (order.index(tid(d)) if tid(d) in order else len(order), d))
    review_types = [(tid(d), d, label_of(tid(d))) for d in folders]

    reviews: list[Review] = []
    for type_id, tfolder, tlabel in review_types:
        for sub in _listdir(repo, f"Review/{tfolder}"):
            d = f"Review/{tfolder}/{sub}"
            if not os.path.isdir(os.path.join(repo, d)):
                continue
            if sub not in by_folder:
                fail(d, f"review folder {sub!r} is not a candidate folder in {cpath}")
            c = by_folder[sub]
            rp = f"{d}/REVIEW.md"
            md = _read(repo, rp)
            h1 = next((l[2:].strip() for l in md.splitlines() if l.startswith("# ")), "")
            m = re.search(r"candidate-\d+", h1)
            bid = m.group() if m else unblind.get(c.slug, "")
            if m and blind.get(bid) != c.slug:
                fail(rp, f"heading names {bid}, but {bpath} maps {bid} to {blind.get(bid)!r}, not {c.slug!r}")
            overall, oline = parse_overall(md, rp)
            files = {n: f"{d}/{n}" for n in ("PROMPT.txt", "REVIEW.md", "TRANSCRIPT.md") if os.path.isfile(os.path.join(repo, d, n))}
            r = Review(type_id, tfolder, tlabel, c.slug, sub, bid, h1, overall, oline, parse_criteria(md, rp), md, d, files)
            for n in _listdir(repo, f"{d}/screenshots"):
                if n.lower().endswith((".png", ".jpg", ".jpeg")):
                    p = f"{d}/screenshots/{n}"
                    w, h = img.size(os.path.join(repo, p))
                    s = Shot(p, "review", r.key, f"{tlabel} review", c.slug, w, h, _caption(md, n))
                    r.shots.append(s)
                    c.shots.append(s)
            reviews.append(r)

    # judges
    mpath = "Judge/judge-mapping.json"
    jmap = _json(repo, mpath) if os.path.exists(os.path.join(repo, mpath)) else {}
    info = _judges_table(repo)
    judges: list[Judge] = []
    present = {}
    for d in _listdir(repo, "Judge"):
        if d.endswith("-Judge") and os.path.isfile(os.path.join(repo, "Judge", d, "RANKING.md")):
            present[d.removesuffix("-Judge").lower()] = d
    for jid in list(jmap) + sorted(set(present) - set(jmap)):
        if jid not in present:  # mapping entry without a RANKING.md: not a judgment (yet); say so
            print(f"build: note: {mpath} has an entry {jid!r} but no Judge/<X>-Judge/RANKING.md for it; not shown", file=sys.stderr)
            continue
        d = present[jid]
        rp = f"Judge/{d}/RANKING.md"
        if jid not in jmap:
            fail(rp, f"judge id {jid!r} has no entry in {mpath}")
        m = jmap[jid]
        mapping, lprompt, alerts = {}, {}, {}
        for letter, v in m.items():
            if v.get("name") not in by_folder:
                fail(mpath, f"{jid}.{letter} maps to {v.get('name')!r}: candidate in a ranking but not in {cpath}")
            cc = by_folder[v["name"]]
            if v.get("prompt") != cc.prompt:
                fail(mpath, f"{jid}.{letter}: prompt {v.get('prompt')!r} differs from {cpath} ({cc.prompt!r} for {cc.slug})")
            other = next((l for l, s in mapping.items() if s == cc.slug), None)
            if other:
                fail(mpath, f"{jid}.{other} and {jid}.{letter} both map to {v['name']!r}")
            mapping[letter], lprompt[letter], alerts[letter] = cc.slug, v["prompt"], int(v.get("alerts_patched", 0))
        md = _read(repo, rp)
        rows = []
        for rank, letter, prompt, just in parse_ranking(md, rp, set(mapping)):
            if prompt != lprompt[letter]:
                fail(rp, f"letter {letter}: table says prompt {prompt!r}, {mpath} says {lprompt[letter]!r}")
            rows.append(RankRow(rank, letter, mapping[letter], prompt, just))
        h1 = next((l[2:].strip() for l in md.splitlines() if l.startswith("# ")), d)
        mat, foc = info.get(d, (None, None))
        files = {n: f"Judge/{d}/{n}" for n in ("PROMPT.txt", "RANKING.md", "MAPPING.md", "TRANSCRIPT.md") if os.path.isfile(os.path.join(repo, "Judge", d, n))}
        shots_dir = f"Judge/{d}/screenshots"
        browser = "browser" in jid.split("_") or bool(_listdir(repo, shots_dir))
        j = Judge(jid, d, label_of(jid), h1, mat, foc, browser, mapping, lprompt, alerts, rows,
                  section(md, "Ranking criteria") or "", parse_special(md, rp, mapping),
                  section(md, "Summary of tests and approach") or "", md, f"Judge/{d}", files)
        for n in _listdir(repo, shots_dir):
            if not n.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            p = f"{shots_dir}/{n}"
            lm = re.match(r"([A-Z])[-_.]", n)
            slug = None
            if lm:
                if lm.group(1) not in mapping:
                    fail(p, f"screenshot prefix {lm.group(1)!r} is not a letter in {mpath}[{jid!r}]")
                slug = mapping[lm.group(1)]
            w, h = img.size(os.path.join(repo, p))
            s = Shot(p, "judge", jid, f"{j.label} judge", slug, w, h, _caption(md, n))
            j.shots.append(s)
            if slug:
                by_folder_slug = next(c for c in cands if c.slug == slug)
                by_folder_slug.shots.append(s)
        judges.append(j)

    for c in cands:
        if c.thumbnail_path and c.thumbnail_path not in {s.path for s in c.shots}:
            fail(cpath, f"candidate {c.slug!r}: thumbnail {c.thumbnail_path!r} is not one of its review or judge screenshots")

    # discarded runs (kept for the record, shown on the methodology page)
    discarded = []
    for sub in _listdir(repo, "ReviewOrchestrator/discarded"):
        d = f"ReviewOrchestrator/discarded/{sub}"
        if not os.path.isdir(os.path.join(repo, d)):
            continue
        files = {n: f"{d}/{n}" for n in _listdir(repo, d) if os.path.isfile(os.path.join(repo, d, n))}
        md = _read(repo, files["REVIEW.md"]) if "REVIEW.md" in files else ""
        shots = []
        for n in _listdir(repo, f"{d}/screenshots"):
            p = f"{d}/screenshots/{n}"
            w, h = img.size(os.path.join(repo, p))
            shots.append(Shot(p, "discarded", sub, "Discarded run", None, w, h, _caption(md, n)))
        discarded.append({"id": sub, "dir": d, "files": files, "shots": shots, "md": md})

    return Model(repo, cands, judges, review_types, reviews, blind, discarded, sha_file)
