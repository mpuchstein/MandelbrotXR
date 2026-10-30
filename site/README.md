# MandelbrotXR results site

A static site that presents this repository's experiment: eight AI coding assistants each built a
standalone WebXR Mandelbrot page; the pages were reviewed blind (phase 1) and ranked by blind judges
(phase 2). Served at <https://mandelbrotxr.puchstein.dev>; deployment notes are in [DEPLOY.md](DEPLOY.md).

## Build

Standard library only (Python ≥ 3.11 for `tomllib`; developed on 3.13). From the repository root:

```bash
python3 -I site/build.py
```

That writes the complete site to `site/dist/` (gitignored). Options:

- `--out DIR`: output directory. It is emptied first; the build refuses to clear a non-empty directory
  that it did not create (marker file `.mandelbrotxr-site`).
- `--base-url URL` (default `https://mandelbrotxr.puchstein.dev/`): used only for QR codes, the Atom feed
  and canonical links. Every other URL is relative, so the output works at any root, e.g.
  `cd site/dist && python3 -m http.server`.
- `--pages a,b`: build only some page modules (development).

The output is deterministic: the same commit gives byte-identical files. The date comes from the
commit, the version from `git rev-parse HEAD` (with `-dirty` if the tree has changes). A shallow clone
is unshallowed first, because the changelog and the feed need the history.

## Tests

```bash
python3 -I site/test_build.py
```

Stdlib only. Checks the mean ranks against `Judge/README.md`, the phase-1 scores against
`ReviewOrchestrator/README.md` §4, every product sha256, every internal link and fragment, that site
pages have no inline scripts, that two builds are byte-identical, that bad data fails loudly, and that
a synthetic 6th judge, 4th review type and 9th candidate build without code changes.

```bash
python3 -I site/check_site.py
```

Browser checks with headless Chromium via Playwright (preinstalled in the build environment; otherwise
`python3 -m pip install --break-system-packages playwright && python3 -m playwright install --with-deps chromium`).
It builds the site, serves it with `python3 -m http.server`, and checks HTTP 200 for every page, zero
console errors, no external requests and no inline scripts on site pages, sorting by every column,
the Blind/Reveal toggles, search, Compare from its URL, every product page, a keyboard-only pass, and
axe-core (pinned `axe-core@4.10.3`, installed with npm into a cache directory on first run) on every page
type in light and dark: zero serious or critical violations.

## Data model

Everything is discovered from the repository; `site/candidates.toml` is the only hand-edited data file.

| Entity | Source | Notes |
|---|---|---|
| Candidate | `site/candidates.toml` (`[[candidate]]`: slug, folder, name, label, vendor, product, model, effort, provenance, prompt, product_file, source_url, date) | `folder/product_file` must match `ReviewOrchestrator/blind/source-html.sha256`; `folder/TRANSCRIPTION.md` is the chat transcript. `label` is the display name used across the site (tables, charts, headings); `name` is a longer descriptive name kept in the data export and search. Colour = position in the file (Okabe–Ito; dash patterns and marker shapes after 8). |
| Review type | every `Review/<Type>-Review/` folder | id = `<type>` lowercased; column order follows `ReviewOrchestrator/README.md` §4, new types are appended alphabetically. |
| Review | `Review/<Type>-Review/<folder>/REVIEW.md` (+ `PROMPT.txt`, `TRANSCRIPT.md`, `screenshots/`) | First table = criteria (`Criterion | Score | reason`); overall score = first number on the "Overall score" line or in an `| Overall | N |` row. The `candidate-NN` in the heading is checked against `ReviewOrchestrator/blind-mapping.json`. |
| Judge | every `Judge/<Type>-Judge/` with `RANKING.md` and an entry in `Judge/judge-mapping.json` | id = folder name lowercased without `-Judge`. `RANKING.md` needs the sections Ranking criteria, Ranking (table `Rank | Candidate | Prompt | Justification`), Special elements (`- **<letters> — <element>**: <reason>`) and Summary of tests and approach. The letter set comes from the mapping, so any number of candidates works. Screenshots named `<Letter>-….jpg` are attributed via the mapping. |

Derived metrics (marked "derived" on the site): mean rank = mean of a candidate's ranks over the judges
that ranked it (candidates not ranked by every judge are listed after those that were); spread = min–max
and population σ of those ranks; agreement = Kendall τ-b between every pair of judges over the candidates
both ranked.

The build fails with a message naming the file when data is inconsistent: a ranked letter missing from
the mapping (or a mapped letter not ranked), a candidate in a ranking or review but not in
`candidates.toml`, an unparsable score, a prompt mismatch, or a sha256 mismatch. Nothing is skipped.

Code layout: `build.py` (entry point) · `sitelib/data.py` (loading, parsing, validation, metrics) ·
`sitelib/layout.py` (page shell, URLs, evidence links) · `sitelib/fragments.py` (shared URLs, colours,
caveats) · `sitelib/md.py` (safe Markdown renderer) · `sitelib/qr.py` (QR encoder) · `sitelib/img.py`
(image sizes, PNG encoder, hero render) · `sitelib/searchindex.py` (search index) · `sitelib/pages/*.py`
(one module per section, run in `ORDER`) · `assets/` (CSS concatenated into `site.css`, JS, favicon).

## Extending

No code changes are needed for any of these. Rebuild and run `python3 -I site/test_build.py` afterwards.

### Add a judgment (a new judge)

1. Create `Judge/<Type>-Judge/` with `RANKING.md` in the format above, plus `PROMPT.txt`, `MAPPING.md`,
   `TRANSCRIPT.md` and optionally `screenshots/<Letter>-<what>.jpg`.
2. Add `"<type>": {"<Letter>": {"name": "<candidate folder>", "prompt": "v0|v1"}, …}` to
   `Judge/judge-mapping.json` (key = folder name lowercased without `-Judge`, e.g. `Browser_HTML-Judge`
   → `browser_html`). Every ranked letter must be mapped and every mapped folder must be in
   `site/candidates.toml`.
3. Commit; the changelog and `feed.xml` gain an entry for the added `RANKING.md`.
4. Optional: add a row for it to the "Judges" table in `Judge/README.md` (material, focus) — the judge
   page shows those columns when present.

### Add a review type

1. Create `Review/<Type>-Review/<candidate folder>/REVIEW.md` (criteria table + overall score line),
   with `PROMPT.txt`, `TRANSCRIPT.md` and optionally `screenshots/`, for each reviewed candidate.
2. If the heading names a `candidate-NN`, it must match `ReviewOrchestrator/blind-mapping.json`.
3. Commit. The type appears as a new score column (after the §4 columns) and on every reviewed
   candidate's page.

### Add a candidate

1. Add the folder `<Vendor>-<Product>-<Model>-<Effort>-v<N>/` with the product HTML and
   `TRANSCRIPTION.md`.
2. Append its checksum to `ReviewOrchestrator/blind/source-html.sha256`:
   `sha256sum <folder>/<file> >> ReviewOrchestrator/blind/source-html.sha256`.
3. Add a `[[candidate]]` table to `site/candidates.toml` with all fields (see the comment at the top of
   the file). Its position fixes its chart colour.
4. Judges and reviews that include it follow the two recipes above; judges that did not rank it show
   "–" and it is listed after the fully ranked candidates.
