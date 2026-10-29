# Brief: MandelbrotXR results site

## Goal
Build a static website, to be served at https://mandelbrotxr.puchstein.dev, that presents this repo's experiment. Eight AI coding assistants each built a standalone WebXR Mandelbrot page. Those pages were then reviewed blind (phase 1) and ranked by 5 blind judges (phase 2).

Visitors must be able to:
1. see the results at a glance;
2. sort and explore the rankings;
3. play every product;
4. follow any number back to the evidence that produced it.

The site must stay maintainable: adding a judge, review type or candidate must not require code changes. Deployment (VPS, Caddy, DNS) is NOT your job. Your job is a build that is correct, complete and ready to serve.

## Read first
- `ReviewOrchestrator/README.md`: process, incidents, file map.
- `Judge/README.md`: phase-2 method and the aggregated rank table. Your build must reproduce this table exactly.
- `prompt0.txt`, `prompt1.txt`: the two task prompts (v0 and v1).
- One example of each data file:
  - `Judge/HTML-Judge/{PROMPT.txt,RANKING.md,MAPPING.md}`
  - `Review/HTML-Review/<folder>/REVIEW.md` and `Review/Browser-Review/<folder>/REVIEW.md`
  - `<folder>/TRANSCRIPTION.md`
- `ReviewOrchestrator/tools/judge_aggregate.py` and `judge_finalize.py:check_ranking`: the existing parsers. Reuse their logic, but they hardcode 8 candidates (A–H) and the 5 judge folders. Don't edit them.

## Data sources (all committed; render nothing else, ignore `__pycache__/`)
| What | Where |
|---|---|
| Candidates (8) | Top-level folders `<Vendor>-<Product>-<Model>-<Effort>-v<N>/`, each with one product `.html` and `TRANSCRIPTION.md` (the chat transcript; its header has source URL, model and effort). |
| Phase-1 reviews (3 types × 8) | `Review/{HTML,TRANSCRIPT,Browser}-Review/<folder>/`: `PROMPT.txt`, `REVIEW.md` (6-criterion 1–10 table plus an overall score), `TRANSCRIPT.md`, and `screenshots/` (browser reviews only). |
| Phase-2 judges (5) | `Judge/<Type>-Judge/`: `PROMPT.txt`, `RANKING.md` (criteria, ranked table by letter, special elements, summary), `MAPPING.md`, `TRANSCRIPT.md`, and `screenshots/` (browser judges only). |
| Letter → candidate | `Judge/judge-mapping.json`, keyed by judge id. A folder's id is its name lowercased with `-Judge` stripped (`HTML_TRANSCRIPT-Judge` → `html_transcript`). Phase-1 blinding: `ReviewOrchestrator/blind-mapping.json` (candidate-NN → folder). |
| Integrity | `ReviewOrchestrator/blind/source-html.sha256` (`<sha>  <folder>/<file>`). |
| Process record | `ReviewOrchestrator/{README,PLAN,PROMPT,PROMPTS,TRANSCRIPT}.md`, `server-logs/`, `discarded/`. |

Parsing gotchas, already verified:
- Overall-score lines in `REVIEW.md` are formatted inconsistently: `Overall score: **4 / 10**`, `8 / 10**`, `5/10`, `2.5 / 10 (rounded: 3)`, and in `TRANSCRIPT-Review/Mistral…` a table row `| **Overall** | **7** |`.
  - Write a tolerant parser and take the first number. For example, Copilot-Interactive's HTML score is 2.5, not 3.
  - `ReviewOrchestrator/README.md` §4 is the ground truth.
- Transcripts are large. The biggest is `ReviewOrchestrator/TRANSCRIPT.md` at about 10.9k lines; the judge logs are about 4.5k lines each.

## Hard constraints
- **Generator:** `site/build.py --out <dir>` (default `site/dist/`, gitignored) writes the complete site.
  - Stdlib first. If you need a library (Markdown rendering, QR codes), pin it via `uv run --with <pkg>==<exact version> python -I site/build.py …`, and document that one-line build command in `site/README.md`. Never assume a global install.
  - Under `python -I`, the script's own directory is NOT on `sys.path`. If you split the build into modules, insert that directory explicitly, as `judge_aggregate.py` does.
  - `--base-url` (default `https://mandelbrotxr.puchstein.dev/`) is used only for QR codes, the Atom feed and canonical links. Everything else uses relative URLs.
- **Determinism:** the same commit must give byte-identical output.
  - Take the date from the commit, never from the wall clock.
  - Take the SHA from `git rev-parse HEAD`, with `-dirty` appended if the tree is dirty.
  - If the clone is shallow, run `git fetch --unshallow` first, since the changelog needs history.
- **Static output only:** plain HTML, CSS and JS that works under `python3 -m http.server` at any root. No server code, cookies or analytics, and no runtime requests to third parties from site pages. Vendor any JS library into the output, with a pinned version and its license file.
  - Prefer charts rendered as inline SVG at build time: they work without JS and need no chart library. Use JS only for interactivity.
- **Site-page CSP:** no inline `<script>` and no `on*=` handlers, so every site page passes `Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'self'`.
- **Products:**
  - Copy each product HTML byte-for-byte to `play/<slug>/index.html`, never modify it, and show its sha256. The sha must match `source-html.sha256`; the build fails otherwise.
  - Products are inline single files, so they need a different CSP (see DEPLOY.md).
  - On their pages, flag that the Gemini product loads three.js r128 and Tailwind from CDNs, and that the Copilot-Autopilot product calls `alert()`. Present both as facts from the reviews.
- **No-JS baseline:** every table is rendered server-side in a sensible default order. JS adds sorting, filters, toggles and search.
- **Faithfulness:**
  - Quote judges and reviewers. Never paraphrase a verdict into a stronger claim.
  - Mark derived metrics (mean rank, spread, Kendall τ) as derived and show how each is computed. Show ties as ties (the two Opus builds share mean rank 1.8).
  - State these caveats prominently:
    - v0 and v1 are different prompts, and each candidate was judged against its own.
    - No real VR or AR session was entered; everything was tested in desktop Chrome.
    - All reviewers and judges were Opus 5.5 agents, and two candidates are Opus 5.5 builds. Put this on the methodology page and keep it neutral.

## Extensibility (discover, don't hardcode)
- **Judges:** every `Judge/*-Judge/` folder that has a `RANKING.md` and an entry in `judge-mapping.json`. The letter set comes from the mapping, so any number of candidates works.
- **Review types:** every `Review/*-Review/` folder.
- **Candidates:** `site/candidates.toml` (parse with stdlib `tomllib`). This is the ONLY hand-edited data file. Fields: slug, folder, vendor, product, model, effort, prompt version, product filename, source chat URL, date. Pre-fill it from the folder names, the `TRANSCRIPTION.md` headers and README §1.
- **Validation:** fail loudly, naming the file, on inconsistent data:
  - a letter missing from the mapping;
  - a candidate in a ranking but not in `candidates.toml`;
  - an unparsable score;
  - a sha mismatch.

  Never skip anything silently.
- **Docs:** `site/README.md` has a short section on how to add a new judgment, review type or candidate, with exact steps.

## Information architecture
1. **Home:**
   - A one-paragraph explainer of the experiment.
   - The headline result as in `Judge/README.md`: consensus top 4, bottom 2, and the two notable dissents.
   - Overview cards for all 8 candidates: thumbnail, mean rank, phase-1 scores, prompt badge, Play button.
   - A compact ranking.
2. **Rankings:**
   - A sortable judge × candidate matrix with mean rank and the phase-1 overall scores. Every column sorts ascending/descending with `aria-sort`, and the sort state lives in the URL hash.
   - Filters: prompt v0/v1, and judge material (static vs. browser).
   - A heatmap toggle.
   - Rank spread (min–max and σ) as a controversy indicator.
   - Below the matrix: a Kendall-τ agreement matrix between judges and a bump chart of ranks across judges.
   - A "how to read this" note.
3. **Candidate pages** (`candidates/<slug>/`):
   - A Play button. It opens the full-page `play/<slug>/`, since WebXR needs a top-level page.
   - A QR code for the product's absolute URL.
   - A gallery of all reviewer and judge screenshots.
   - A radar or bar chart of the 6 phase-1 criteria per review type, with the reviewers' one-line reasons.
   - Every judge's rank and verbatim justification, each linked to its source.
   - The special elements credited to this candidate.
   - Facts: bytes, sha256, external dependencies, prompt version, model and effort as recorded.
   - Links to the chat transcript and the reviews.
4. **Compare:** pick any 2 candidates and see them side by side: scores, ranks, justifications, screenshots. The selection lives in the URL.
5. **Special-elements catalog:**
   - Every "Special elements" bullet from every judge, grouped by technique (perturbation deep zoom, Cardboard stereo, gaze-dwell, …) and cross-linked to candidates.
   - A section on claim-vs-code mismatches and hallucinations reported by the transcript and HTML+transcript judges and reviewers, quoted and linked.
6. **Judges and reviews:**
   - One page per judge: material, prompt, criteria, ranking, summary, transcript.
   - A **Blind/Reveal toggle** on each judge page: first the letters A–H as the judge saw them, then the names revealed via the mapping.
   - One page per review. Show the phase-1 candidate-NN blinding the same way.
7. **Transcripts:** rendered chat transcripts and agent logs. Split them or render them lazily, collapse thinking and tool output, and add an anchor per message.
8. **Methodology:**
   - A pipeline diagram: extract → blind → review → judge → aggregate.
   - Blinding, the effort deviation, serving, and environment limits.
   - Every incident from both READMEs, stated plainly: over-redaction, the cached c02 run, `alert()`, the privacy rewrite.
   - Both prompts verbatim, with links to the orchestrator prompts and log.
9. **Search:** client-side full-text search over reviews, rankings, judge summaries and transcripts, from an index built at build time. Use a small vendored library or hand-roll one. It must stay fast on a phone.
10. **Data and changes:**
    - `data/results.json` plus CSVs (ranks, scores, criteria) with a documented schema, linked from a Data page.
    - A Changelog page and `feed.xml` (Atom) generated from the git history of `Judge/` and `Review/`, with one entry per added judgment.
11. **Every page:** a footer with the build commit SHA and date. Evidence links go to `https://github.com/mpuchstein/MandelbrotXR/blob/<sha>/<path>`, alongside the locally rendered copy.

## Design
Beautiful, calm and data-first: this is a results report, not a landing page.
- Dark and light themes (`prefers-color-scheme` plus a toggle). Use a Mandelbrot-inspired palette with restraint. The hero may use a product screenshot or a tiny local canvas render, never a CDN.
- Mobile-first: the site must be fully usable at 390 px. Tables scroll inside their own container, never the page.
- WCAG 2.1 AA:
  - contrast, keyboard-sortable headers, focus rings, alt text on screenshots, and `prefers-reduced-motion`;
  - every chart has a table or text equivalent and colorblind-safe colors.
- Fast: lazy images, no layout shift, and small site JS (products excluded).
- Consistent navigation with breadcrumbs.

## Deliverables
- `site/build.py` (plus modules if needed), `site/candidates.toml`, and `site/assets/` (CSS, JS, vendored libraries with their licenses).
- `site/README.md`: the build command, the data model, and how to extend the site.
- `site/test_build.py`: assert-based and stdlib-only, run with `python3 -I site/test_build.py`. It checks that:
  - the mean ranks equal those in `Judge/README.md` (1.8, 1.8, 3.0, 3.4, 5.6, 5.8, 6.8, 7.8);
  - the phase-1 overall scores equal README §4;
  - every product sha matches;
  - every internal link in the output resolves;
  - a synthetic 6th judge and 9th candidate, added in a temporary copy of the repo, build without code changes.
- `site/check_site.py`: the Playwright check (see Done when).
- `site/DEPLOY.md`, recommendations only, for the owner to apply:
  - Caddy headers: the CSP above for site pages. For `/play/*`, either no CSP or one that allows inline scripts plus the Gemini CDNs, and a `Permissions-Policy` that allows `xr-spatial-tracking`, `gyroscope`, `accelerometer` and `magnetometer` for `self`.
  - `Cache-Control` advice, and `hide .git`.
  - A note that WebXR requires HTTPS.
  - The exact build command and output directory.
- `.gitignore`: add `site/dist/`. Never commit build output.
- `site/screenshots/`: PNGs of every page type at 390×844 and 1440×900, in light and dark, so the owner can review without building.

## Done when
1. The documented build command succeeds from a clean clone, and `python3 -I site/test_build.py` passes.
2. `site/check_site.py` passes. It uses headless Chromium via Playwright, which the environment setup preinstalls; if it is missing, run `python3 -m pip install --break-system-packages playwright && python3 -m playwright install --with-deps chromium`. Pass `--use-angle=swiftshader --enable-unsafe-swiftshader` for WebGL. Against `python3 -m http.server` serving the build output, it checks that:
   - every generated page returns HTTP 200;
   - site pages log zero console errors;
   - the rankings sort by every column;
   - Blind/Reveal toggles;
   - a search returns hits;
   - Compare opens from its URL;
   - every product page loads.
3. Two consecutive builds are byte-identical.
4. Site pages have no inline scripts and make no external requests; assert this from the Playwright network log.
5. An independent review pass, by an agent with none of the builder's context, checks every requirement in this brief one by one and checks that quoted verdicts are faithful. Fix each finding, or answer it explicitly in the PR description.

## Process
- Work on branch `site-v1`. Make small conventional commits with NO `Co-Authored-By` or other attribution trailers.
- Open a PR to `main`. Its description holds the Done-when checklist with evidence, plus screenshots.
- Edit nothing outside `site/` and `.gitignore`, and don't edit `site/BRIEF.md`. If source data looks wrong, list it in the PR; don't fix it.
- If a requirement turns out to be impossible or contradictory, pick the most faithful option, note it in the PR, and continue without stopping to ask.
