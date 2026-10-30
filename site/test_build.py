"""Assert-based build tests (stdlib only). Run: python3 -I site/test_build.py

Checks: mean ranks and the aggregated table equal Judge/README.md; phase-1 overall scores equal
ReviewOrchestrator/README.md §4; every product copy matches source-html.sha256; every internal link
and fragment in the output resolves; site pages carry no inline scripts or handlers; two builds are
byte-identical; validation fails loudly (naming the file) on inconsistent data; and a synthetic 6th
judge, 4th review type and 9th candidate, added in a temporary copy of the repo, build without code
changes.
"""
import hashlib
import html.parser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)  # python -I does not put the script's directory on sys.path

from sitelib import data  # noqa: E402

EXPECTED_MEANS = ["1.8", "1.8", "3.0", "3.4", "5.6", "5.8", "6.8", "7.8"]


def build(repo: str, out: str, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", os.path.join(repo, "site", "build.py"), "--out", out, *extra],
                          capture_output=True, text=True)


def build_ok(repo: str, out: str) -> None:
    r = build(repo, out)
    assert r.returncode == 0, f"build failed ({r.returncode}):\n{r.stdout}\n{r.stderr}"


def md_table(md: str, after: str) -> list[list[str]]:
    """Rows (cells) of the first table after the line starting with `after`."""
    lines = md.split("\n")
    i = next(n for n, l in enumerate(lines) if l.startswith(after))
    rows = []
    for l in lines[i + 1:]:
        if l.startswith("|"):
            rows.append(l)
        elif rows:
            break
    return [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]


# ---------------------------------------------------------------- data checks

def test_mean_ranks(model: data.Model) -> None:
    means = [data.fmt_mean(model.mean_rank(c.slug)) for c in model.ordered()]
    assert means == EXPECTED_MEANS, means
    readme = open(os.path.join(REPO, "Judge/README.md"), encoding="utf-8").read()
    block = readme.split("## Result", 1)[1].split("\n")
    table = []
    for line in block[1:]:
        if line.startswith("|"):
            table.append(line)
        elif table:
            break
    assert model.rank_table_md() == "\n".join(table), f"aggregated table differs from Judge/README.md:\n{model.rank_table_md()}"
    opus = [c for c in model.candidates if c.folder.startswith("Anthropic-")]
    st = model.standing()
    assert len(opus) == 2 and all(st[c.slug] == (1, True) for c in opus), "the two Opus builds must tie for first"


def test_phase1_scores(model: data.Model) -> None:
    readme = open(os.path.join(REPO, "ReviewOrchestrator/README.md"), encoding="utf-8").read()
    rows = md_table(readme, "## 4. Results")
    head, body = rows[0], [r for r in rows[2:]]
    types = {t_label.lower(): t_id for t_id, _, t_label in model.review_types}
    seen = 0
    for r in body:
        folder = r[0]
        for col, val in zip(head[1:], r[1:]):
            rev = next(x for x in model.reviews if x.folder == folder and x.type_id == types[col.lower()])
            assert rev.overall == float(val), (folder, col, rev.overall, val)
            seen += 1
    assert seen == len(model.reviews) == 24, seen
    inter = next(x for x in model.reviews if x.folder == "GitHub-CopilotTasks-Auto-Interactive-v1" and x.type_id == "html")
    assert inter.overall == 2.5, inter.overall


# ---------------------------------------------------------------- output checks

def test_products(model: data.Model, out: str) -> None:
    sums = {}
    for line in open(os.path.join(REPO, model.sha_file), encoding="utf-8"):
        if line.strip():
            h, _, p = line.partition("  ")
            sums[p.strip()] = h
    for c in model.candidates:
        got = open(os.path.join(out, "play", c.slug, "index.html"), "rb").read()
        assert got == open(os.path.join(REPO, c.html_path), "rb").read(), c.slug
        assert hashlib.sha256(got).hexdigest() == sums[c.html_path], c.slug


class _Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids, self.inline_scripts, self.handlers = [], set(), 0, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "name" in a:
            self.ids.add(a["name"])
        for k in ("href", "src", "action", "data-index", "data-root"):
            if a.get(k) is not None and not (tag == "link" and a.get("rel") == "canonical"):
                self.links.append((tag, k, a[k], a.get("rel", "")))
        if tag == "script" and not a.get("src"):
            self.inline_scripts += 1
        self.handlers += [k for k in a if k.lower().startswith("on")]


_parsed: dict[str, _Links] = {}


def _parse(path: str) -> _Links:
    if path not in _parsed:
        p = _Links()
        p.feed(open(path, encoding="utf-8").read())
        _parsed[path] = p
    return _parsed[path]


def site_pages(out: str) -> list[str]:
    pages = []
    for d, dirs, files in os.walk(out):
        dirs.sort()
        rel = os.path.relpath(d, out)
        if rel == "play" or rel.startswith("play" + os.sep):
            continue  # products are copied verbatim; not site pages
        pages += [os.path.join(d, f) for f in sorted(files) if f.endswith(".html")]
    return pages


def test_links(out: str) -> int:
    """Every internal href/src/action resolves to a file, and every #fragment to an id."""
    bad, n = [], 0
    for page in site_pages(out):
        p = _parse(page)
        assert p.inline_scripts == 0, f"{page}: inline <script>"
        assert not p.handlers, f"{page}: inline handlers {p.handlers}"
        for tag, attr, url, rel in p.links:
            u = urllib.parse.urlsplit(url)
            if u.scheme or url.startswith("//"):
                assert u.scheme in ("http", "https", "mailto"), f"{page}: unexpected URL scheme in {url!r}"
                assert tag in ("a", "form") or (tag == "link" and rel == "alternate"), f"{page}: external resource <{tag}> {url}"
                continue
            n += 1
            target = page if not u.path else os.path.normpath(os.path.join(os.path.dirname(page), urllib.parse.unquote(u.path)))
            if u.path.endswith("/") or os.path.isdir(target):
                target = os.path.join(target, "index.html")
            if not os.path.exists(target):
                bad.append(f"{os.path.relpath(page, out)}: {attr}={url!r} -> missing {os.path.relpath(target, out)}")
                continue
            if u.fragment and target.endswith(".html") and urllib.parse.unquote(u.fragment) not in _parse(target).ids:
                frag = urllib.parse.unquote(u.fragment)
                if "=" not in frag and frag != "reveal":  # 'k=v' / 'reveal' fragments are JS view state, not ids
                    bad.append(f"{os.path.relpath(page, out)}: {url!r} -> no id {frag!r} in {os.path.relpath(target, out)}")
    assert not bad, f"{len(bad)} broken internal links:\n" + "\n".join(bad[:50])
    return n


def tree_digest(out: str) -> dict[str, str]:
    d = {}
    for root, dirs, files in os.walk(out):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(root, f)
            d[os.path.relpath(p, out)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return d


def test_results_json(out: str) -> None:
    res = json.load(open(os.path.join(out, "data", "results.json"), encoding="utf-8"))
    assert isinstance(res, dict) and res.get("candidates"), "results.json has no candidates"


def test_thumbnails(model: data.Model, out: str) -> None:
    home = open(os.path.join(out, "index.html"), encoding="utf-8").read()
    for c in model.candidates:
        if c.thumbnail_path:
            assert c.thumbnail_path in home, f"home card of {c.slug} ignores its candidates.toml thumbnail"


# ---------------------------------------------------------------- validation and extensibility

def copy_repo(dst: str) -> str:
    ign = shutil.ignore_patterns("dist", "__pycache__")
    shutil.copytree(REPO, dst, ignore=ign, symlinks=True)
    return dst


def expect_failure(repo: str, needle: str, path_hint: str) -> None:
    try:
        data.load(repo)
    except data.DataError as e:
        assert path_hint in str(e) and needle in str(e), f"wrong error: {e}"
        return
    raise AssertionError(f"expected DataError mentioning {path_hint!r} / {needle!r}")


def edit(path: str, fn) -> str:
    old = open(path, encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(fn(old))
    return old


def test_validation(tmp: str) -> None:
    repo = copy_repo(os.path.join(tmp, "val"))
    J = os.path.join(repo, "Judge/judge-mapping.json")
    # a letter missing from the mapping
    old = edit(J, lambda s: json.dumps({k: ({l: v for l, v in m.items() if l != "H"} if k == "html" else m) for k, m in json.loads(s).items()}))
    expect_failure(repo, "missing from Judge/judge-mapping.json", "Judge/HTML-Judge/RANKING.md")
    open(J, "w", encoding="utf-8").write(old)
    # two letters of one judge mapped to the same candidate
    old = edit(J, lambda s: json.dumps({k: ({**m, "B": m["A"]} if k == "html" else m) for k, m in json.loads(s).items()}))
    expect_failure(repo, "both map to", "Judge/judge-mapping.json")
    open(J, "w", encoding="utf-8").write(old)
    # two blind ids mapped to the same candidate
    B = os.path.join(repo, "ReviewOrchestrator/blind-mapping.json")
    old = edit(B, lambda s: json.dumps({k: (json.loads(s)["candidate-01"] if k == "candidate-02" else v) for k, v in json.loads(s).items()}))
    expect_failure(repo, "both map to", "ReviewOrchestrator/blind-mapping.json")
    open(B, "w", encoding="utf-8").write(old)
    # a candidate in a ranking but not in candidates.toml
    old = edit(J, lambda s: json.dumps({k: ({**m, "A": {**m["A"], "name": "Unknown-Model-v1"}} if k == "html" else m) for k, m in json.loads(s).items()}))
    expect_failure(repo, "candidate in a ranking but not in site/candidates.toml", "Judge/judge-mapping.json")
    open(J, "w", encoding="utf-8").write(old)
    # a source_url that disagrees with the transcript header
    T = os.path.join(repo, "site/candidates.toml")
    old = edit(T, lambda s: s.replace("https://claude.ai/chat/09e85d21-ad05-4fe0-b10d-8ef14cc23da7", "https://claude.ai/chat/wrong", 1))
    expect_failure(repo, "differs from the '- Source:' line", "site/candidates.toml")
    open(T, "w", encoding="utf-8").write(old)
    # a thumbnail that is another candidate's screenshot
    old = edit(T, lambda s: s.replace("screenshots/H-room.jpg", "screenshots/C-overview.jpg", 1))
    expect_failure(repo, "is not one of its review or judge screenshots", "site/candidates.toml")
    open(T, "w", encoding="utf-8").write(old)
    # an unparsable score
    R = os.path.join(repo, "Review/HTML-Review/OpenAI-Web-GPT6-Pro-v0/REVIEW.md")
    old = edit(R, lambda s: re.sub(r"(?im)^.*overall score.*$", "**Overall score: excellent**", s))
    expect_failure(repo, "overall score", "Review/HTML-Review/OpenAI-Web-GPT6-Pro-v0/REVIEW.md")
    open(R, "w", encoding="utf-8").write(old)
    old = edit(R, lambda s: s.replace("| 8 |", "| eight |", 1))
    expect_failure(repo, "unparsable criterion score", "Review/HTML-Review/OpenAI-Web-GPT6-Pro-v0/REVIEW.md")
    open(R, "w", encoding="utf-8").write(old)
    # a sha mismatch
    P = os.path.join(repo, "OpenAI-Web-GPT6-Pro-v0/mandelbrot-room.html")
    with open(P, "ab") as f:
        f.write(b"\n")
    expect_failure(repo, "sha256 mismatch", "ReviewOrchestrator/blind/source-html.sha256")
    data.load  # repo copy is discarded afterwards


SYN_FOLDER = "Synthetic-TestBench-Model9-Default-v1"
SYN_SLUG = "synthetic-model9-v1"


def add_synthetic(repo: str) -> None:
    """A 9th candidate, a 6th judge (ranking 9 letters A–I) and a 4th review type."""
    os.makedirs(os.path.join(repo, SYN_FOLDER))
    product = b"<!doctype html><title>Synthetic</title><p>Synthetic test product.</p>\n"
    open(os.path.join(repo, SYN_FOLDER, "synthetic.html"), "wb").write(product)
    open(os.path.join(repo, SYN_FOLDER, "TRANSCRIPTION.md"), "w").write(
        "# Transcription: synthetic test chat\n\n- Source: https://example.invalid/chat\n\n---\n\n## User\n\nBuild it.\n\n---\n\n## Assistant\n\nDone.\n")
    with open(os.path.join(repo, "ReviewOrchestrator/blind/source-html.sha256"), "a") as f:
        f.write(f"{hashlib.sha256(product).hexdigest()}  {SYN_FOLDER}/synthetic.html\n")
    with open(os.path.join(repo, "site/candidates.toml"), "a") as f:
        f.write(f'''
[[candidate]]
slug = "{SYN_SLUG}"
folder = "{SYN_FOLDER}"
name = "Synthetic Model 9 · v1"
label = "Synthetic 9 · v1"
vendor = "TestBench"
product = "Synthetic"
model = "model-9"
effort = "default"
provenance = "synthetic test fixture"
prompt = "v1"
product_file = "synthetic.html"
source_url = "https://example.invalid/chat"
date = "2026-10-30"
''')
    bm = os.path.join(repo, "ReviewOrchestrator/blind-mapping.json")
    m = json.load(open(bm))
    m["candidate-09"] = {"name": SYN_FOLDER, "prompt": "prompt1.txt", "original_html": "synthetic.html"}
    json.dump(m, open(bm, "w"), indent=1)

    model = data.load(repo)
    folders = [c.folder for c in model.candidates]
    letters = [chr(ord("A") + i) for i in range(len(folders))]
    jm = os.path.join(repo, "Judge/judge-mapping.json")
    mapping = json.load(open(jm))
    mapping["synthetic"] = {l: {"name": f, "prompt": model.candidates[i].prompt} for i, (l, f) in enumerate(zip(letters, folders))}
    json.dump(mapping, open(jm, "w"), indent=1)
    jd = os.path.join(repo, "Judge/Synthetic-Judge")
    os.makedirs(jd)
    rows = "\n".join(f"| {r} | {l} | {model.candidates[letters.index(l)].prompt} | Synthetic justification for {l}. |"
                     for r, l in enumerate(reversed(letters), 1))
    open(os.path.join(jd, "RANKING.md"), "w").write(f"""# Synthetic Judge — blind ranking

## Ranking criteria

1. **Synthetic (100%)**: a test criterion.

## Ranking

| Rank | Candidate | Prompt | Justification |
|---|---|---|---|
{rows}

## Special elements

- **{letters[-1]} — synthetic perturbation deep zoom**: a synthetic special element.
- **A, B — synthetic shared element**: another one.

## Summary of tests and approach

Synthetic summary.
""")
    open(os.path.join(jd, "PROMPT.txt"), "w").write("Synthetic judge prompt.\n")
    open(os.path.join(jd, "MAPPING.md"), "w").write("# Synthetic Judge: label mapping\n")
    open(os.path.join(jd, "TRANSCRIPT.md"), "w").write("# Agent transcript: Synthetic-Judge\n\n### User · 2026-10-30T00:00:00Z\n\nRank them.\n\n### Assistant · 2026-10-30T00:00:01Z\n\nRanked.\n")
    for folder, score in ((SYN_FOLDER, "6"), (folders[0], "7.5")):
        rd = os.path.join(repo, "Review/Synthetic-Review", folder)
        os.makedirs(rd)
        open(os.path.join(rd, "REVIEW.md"), "w").write(f"""# Synthetic Review

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Synthetic criterion | {score}/10 | A synthetic reason. |

## Overall score: {score} / 10
""")
        open(os.path.join(rd, "PROMPT.txt"), "w").write("Synthetic review prompt.\n")


def test_synthetic(tmp: str) -> None:
    repo = copy_repo(os.path.join(tmp, "syn"))
    add_synthetic(repo)
    out = os.path.join(tmp, "syn-out")
    build_ok(repo, out)
    for rel in (f"candidates/{SYN_SLUG}/index.html", f"play/{SYN_SLUG}/index.html", "judges/synthetic/index.html",
                f"reviews/synthetic/{SYN_SLUG}/index.html", "rankings/index.html"):
        assert os.path.exists(os.path.join(out, rel)), f"synthetic build lacks {rel}"
    rk = open(os.path.join(out, "rankings/index.html"), encoding="utf-8").read()
    assert "Synthetic" in rk and SYN_SLUG in rk, "rankings page lacks the synthetic judge/candidate"
    model = data.load(repo)
    assert len(model.judges) == 6 and len(model.candidates) == 9 and len(model.review_types) == 4
    assert model.ranks(SYN_SLUG) == {"synthetic": 1}, model.ranks(SYN_SLUG)
    # ranked by one judge of six: no standing, and outside the home page's top/bottom comparison
    page = open(os.path.join(out, f"candidates/{SYN_SLUG}/index.html"), encoding="utf-8").read()
    assert "Ranked by 1 of 6 judges" in page and "Not ranked by any judge" not in page, "candidate page misstates a partial ranking"
    cards = open(os.path.join(out, "candidates/index.html"), encoding="utf-8").read()
    card = next(a for a in cards.split("<article")[1:] if SYN_SLUG in a)
    assert "ranked by 1 of 6 judges" in card and "not ranked by any judge" not in card, "candidate card misstates a partial ranking"
    home = open(os.path.join(out, "index.html"), encoding="utf-8").read()
    i = home.index("<h4>Bottom ")
    assert "Synthetic 9" not in home[i:home.index("</div>", i)], "home bottom-k lists a candidate that not every judge ranked"
    assert "Not in this comparison" in home, "home check does not name the partially ranked candidate"
    res = json.load(open(os.path.join(out, "data/results.json"), encoding="utf-8"))
    assert any(c.get("slug") == SYN_SLUG for c in res["candidates"])
    test_links(out)


def test_parsers() -> None:
    """Formats a later review or judge may use, beyond the ones in the repo today."""
    for line in ("**Overall score (1–10)**: 7 / 10", "| **Overall score (1–10)** | **7** |"):
        assert data.parse_overall(line, "x")[0] == 7, f"{line!r} parsed as {data.parse_overall(line, 'x')[0]}"
    md = "## Special elements\n\n- **C — zoom claim vs code:** the transcript promises: zoom\n"
    s = data.parse_special(md, "x", {"C": "c"})[0]
    assert (s.title, s.reason) == ("zoom claim vs code", "the transcript promises: zoom"), (s.title, s.reason)


def test_home_ties(model: data.Model) -> None:
    """The home page's derived check reports a mean-rank tie at the boundary of the row it belongs to."""
    from types import SimpleNamespace
    from sitelib.pages import home
    ranked = [c.slug for c in model.ordered()]
    means = {s: model.mean_rank(s) for s in ranked}
    means[ranked[-3]] = means[ranked[-2]]  # a tie across the bottom-2 boundary only
    model.mean_rank = means.get
    rows = home.derived_check(SimpleNamespace(model=model), 4, 2).split('<div class="home-check-row">')
    assert "ties with" not in rows[1], "the top row reports a tie that sits at the bottom boundary"
    assert "ties with the first of them" in rows[2], "the bottom row misses the tie at its boundary"


# ---------------------------------------------------------------- main

def main() -> None:
    model = data.load(REPO)
    test_mean_ranks(model)
    test_phase1_scores(model)
    print("ok  mean ranks, aggregated table and phase-1 scores match the READMEs")
    test_home_ties(data.load(REPO))
    print("ok  home page tie notes sit at the boundary of their own row")
    test_parsers()
    print("ok  parsers skip a score scale and keep a colon-in-bold special-element title")
    with tempfile.TemporaryDirectory(prefix="mxr-test-") as tmp:
        a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
        build_ok(REPO, a)
        test_products(model, a)
        print("ok  every product copy matches source-html.sha256")
        n = test_links(a)
        print(f"ok  {n} internal links resolve; no inline scripts or handlers in {len(site_pages(a))} site pages")
        test_results_json(a)
        test_thumbnails(model, a)
        print("ok  home cards use the candidates.toml thumbnails")
        build_ok(REPO, b)
        da, db = tree_digest(a), tree_digest(b)
        diff = sorted(k for k in set(da) | set(db) if da.get(k) != db.get(k))
        assert not diff, f"builds differ: {diff[:20]}"
        print(f"ok  two builds are byte-identical ({len(da)} files)")
        test_validation(tmp)
        print("ok  validation fails loudly, naming the file")
        test_synthetic(tmp)
        print("ok  synthetic 6th judge, 4th review type and 9th candidate build without code changes")
    print("all tests passed")


if __name__ == "__main__":
    main()
