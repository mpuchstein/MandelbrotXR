# Review orchestration log

This file records how the MandelbrotXR outputs were collected and reviewed on 2026-10-29: inputs, steps, decisions, incidents and results. One Claude Code session (Opus 5.5) did the orchestration; its prompt is in `PROMPT.md`, its log in `TRANSCRIPT.md`, and the approved plan in `PLAN.md`.

## 1. Inputs: the 8 chats

| Folder | Source | Prompt | How model/effort were determined | Deliverable (bytes) |
|---|---|---|---|---|
| `OpenAI-Web-GPT6-Pro-v0` | chatgpt.com/c/6ae355ca… | v0 | user's example name; UI shows "Thinking effort: Pro" | `mandelbrot-room.html` (630,552) |
| `OpenAI-Web-GPT6-Pro-v1` | chatgpt.com/c/6ae356bd… | v1 | same UI; confirmed by user | `mandelbrot-room.html` (655,952) |
| `Anthropic-Web-Opus5.5-Max-v0` | claude.ai/chat/09e85d21… | v0 | conversation JSON: `claude-opus-5-5`, `effort_level: max` | `mandelbrot-room.html` (668,223) |
| `Anthropic-Web-Opus5.5-Max-v1` | claude.ai/chat/0a5ff96f… | v1 | conversation JSON: `claude-opus-5-5`, `effort_level: max` | `mandelbrot-xr.html` (111,928) |
| `Mistral-VibeCode-MistralLarge4-Default-v1` | chat.mistral.ai/code/… | v1 | the UI shows no model; the user said "Mistral Large 4" | `mandelbrot-xr.html` (42,451), copied from the final code block |
| `Google-Web-Gemini4Argon-High-v1` | gemini.google.com/app/bb0b8f67… | v1 | model picker "4 Argon", Denkaufwand "Hoch" | `holographic_3d_mandelbrot_webxr_sanctuary.html` (100,163) |
| `GitHub-CopilotTasks-Auto-Autopilot-v1` | github.com/copilot/tasks/b471892c… | v1 | user: model Auto, mode Autopilot, approval Allow all. The composer label shows "Autopilot". The model tooltip shows that Auto resolved to `gpt-5.6-luna` | `mandelbrot-xr.html` (13,027) |
| `GitHub-CopilotTasks-Auto-Interactive-v1` | github.com/copilot/tasks/1976d0f6… | v1 | user: model Auto, mode Interactive, approval Assisted. The composer label shows "Interactive". The model tooltip shows that Auto resolved to `gpt-5.6-luna` | `mandelbrot-xr.html` (11,490) |

`prompt0.txt` is the v0 prompt (three.js + three.xr.js) and `prompt1.txt` is the v1 prompt (WebXR, "highest possible visual wow effect"). Both are verbatim from the chats.

## 2. Steps

1. **Plan** (plan mode): I surveyed the chats read-only and asked the user about naming, transcript scope, the review brief and the final push. Decisions: detect model names and confirm them with the user, transcripts contain "everything visible", reviews are blind with a shared rubric, and the reviews get committed and pushed.
2. **Extraction** via Claude in Chrome, one chat at a time:
   - ChatGPT: expand "Worked for …", read the page text, download the file from the preview.
   - claude.ai: conversation JSON via the web app's own API, rendered with `tools/claude2md.py`; artifact via "Download as HTML".
   - Mistral: scroll the virtualized page to the top, read the page text, copy the HTML from the final code block.
   - Gemini: page text; Canvas → Exportieren → "Code herunterladen".
   - Copilot: page text; Artifacts → "Download code".
   - The user confirmed the folder names before anything was written to the repo.
3. **Commit 1** `93fc84c`: the extraction folders, `prompt0.txt` and `prompt1.txt`.
4. **Blind setup** (`tools/blind.py`): the 8 folders were shuffled with a fixed seed into `candidate-01…08`, using copies of the HTML (as `index.html`) and anonymized transcripts (identifying header dropped; vendor, product and model names replaced). `blind-mapping.json` holds the mapping. `blind/` contains exactly the transcripts the reviewers read. `blind/*.sha256` shows that the HTML copies are byte-identical to the sources.
5. **Prompts** (`tools/prompts.py`): one template per review type with a shared 6-criterion 1–10 rubric, the matching prompt version quoted, and output written to a blind path. Each prompt was saved as `PROMPT.txt` before its agent launched. For every agent, the prompt in its log matches its `PROMPT.txt`; `tools/finalize.py` checks this.
6. **HTML and transcript reviews:** 16 agents ran in parallel (general-purpose, Opus). Five launches first failed with "Lock file is already being held" and were relaunched unchanged.
7. **Browser reviews:** 8 agents ran one after another. Before each, a `python3 -m http.server` served only that candidate's folder; the logs are in `server-logs/`.
8. **Finalize** (`tools/finalize.py`): reviews and screenshots were copied from the blind paths into `Review/<Type>-Review/<folder>/`, and each agent's session log was rendered to `TRANSCRIPT.md` (`tools/jsonl2md.py`). All 25 agents were shut down afterwards, and the transcripts were re-rendered to include the shutdown exchange.
9. **Commit 2**: the reviews and this folder. The first push (`ab6087c`) leaked personal data (see 3.6). That commit was rewritten and force-pushed.

## 3. Deviations and incidents

1. **Effort:** the agents were requested with `effort: "xhigh"`. Their API requests show `output_config.effort = "high"`, the same as the orchestrator session, so this harness did not pass xhigh through to teammates.
2. **Candidate-02 browser review was rerun:** the first run (`browser-c02`) was served on `localhost:8765`, the same origin as candidate-01 just before, and it reviewed candidate-01's cached page ("The infinite room."). That was caught from its summary and confirmed by `server-logs/http-02.log` (304 responses) and the page titles. The run was discarded and is kept in `discarded/browser-c02-cached-run/`. It was rerun as `browser-c02-rerun` on `localhost:8702`. From then on every candidate had its own port, 8702–8708, and the browser `PROMPT.txt` files for 02–08 were rewritten to that port before launch.
3. **Blocking `alert()`:** candidate-04's Enter VR/AR buttons open a native `alert()`, which blocks the browser extension. The user dismissed it by hand. The orchestrator then told `browser-c04` to stop clicking and to stub `window.alert`. Its first draft had called the buttons silent; it corrected the review (issue #1, steps 3–4b, two scores) after being told about the alert. Before launch, the prompts for 05–08 got a dialog-stub instruction, and their `PROMPT.txt` files contain it.
4. **Browser test limits:** desktop Chrome with no XR device and no WebXR emulator, so no real VR or AR session was entered. The window manager kept the viewport at about 446 px wide. Chrome throttled background windows, so several reviewers could not judge frame rate.
5. **Transcript scope:** "everything visible" means the top-level text with thinking expanded. Nested tool-call groups appear only as the UI's one-line summaries. In Gemini, the second user turn has no visible text, which looks like Canvas's automatic "fix error" request.
6. **Privacy:** the repo is public. The first render of `TRANSCRIPT.md` contained raw tool output from the orchestrator session: the user's Gemini sidebar (chat titles, location) and `~/Downloads` file names. The user chose redaction plus a history rewrite. `tools/redact.py` builds its term list from the session log itself (Gemini page-text dumps and foreign `ls` entries); a private, uncommitted list adds the fragments quoted in prose. Every matching string is replaced with `[redacted]`, and the script fails if any term survives. `ab6087c` was replaced by a new commit and force-pushed. GitHub may keep the old SHA reachable for a while.

## 4. Results: overall scores (1–10)

| Folder | HTML | Transcript | Browser |
|---|---|---|---|
| Anthropic-Web-Opus5.5-Max-v0 | 8 | 8 | 8 |
| Anthropic-Web-Opus5.5-Max-v1 | 8.5 | 7 | 8 |
| OpenAI-Web-GPT6-Pro-v0 | 7.5 | 7 | 8 |
| OpenAI-Web-GPT6-Pro-v1 | 7.5 | 8 | 8 |
| Google-Web-Gemini4Argon-High-v1 | 6 | 4 | 7 |
| Mistral-VibeCode-MistralLarge4-Default-v1 | 5 | 7 | 5 |
| GitHub-CopilotTasks-Auto-Autopilot-v1 | 2 | 4 | 4 |
| GitHub-CopilotTasks-Auto-Interactive-v1 | 2.5 | 4 | 4 |

The HTML reviewers checked these XR-breaking defects against the source with node:
- **Autopilot:** the XR frame callback shadows its own name, so the loop dies after one frame.
- **Interactive:** the per-eye uv and the camera direction are wrong, so the stereo pair can't fuse.
- **Mistral:** `rigYaw = π` and mixed coordinate spaces, so users spawn facing away and AR places the object behind them.

## 4b. Phase 2: comparative judges

Five more blind agents (Opus 5.5, effort high) each ranked all 8 implementations: HTML, transcript, HTML + transcript, browser, and browser + HTML. Method, de-anonymized ranks and incidents are in `../Judge/README.md`. Tools: `judge_blind.py`, `judge_prompts.py`, `judge_finalize.py`, `judge_aggregate.py`. For phase 2, `blind.py` got an import guard; its output is byte-identical to before.

## 5. File map

```
<folder>/                      extracted HTML + TRANSCRIPTION.md (8x)
prompt0.txt, prompt1.txt
Review/{HTML,TRANSCRIPT,Browser}-Review/<folder>/
    PROMPT.txt  REVIEW.md  TRANSCRIPT.md  [screenshots/]
ReviewOrchestrator/
    PROMPT.md  TRANSCRIPT.md  PLAN.md  README.md (this file)
    blind-mapping.json         candidate-NN → folder
    blind/                     anonymized transcripts the reviewers saw + HTML checksums
    server-logs/               http.server access logs per browser review
    discarded/browser-c02-cached-run/   invalid run, kept for the record
    tools/                     claude2md, blind, prompts, finalize, jsonl2md, redact,
                               judge_blind, judge_prompts, judge_finalize, judge_aggregate
Judge/<Type>-Judge/            PROMPT.txt  RANKING.md  TRANSCRIPT.md  MAPPING.md  [screenshots/]
Judge/README.md, Judge/judge-mapping.json
```

## 6. Reproducing the pipeline

The scripts take paths as arguments and use only the standard library. Run them with `python3 -I`.
- `claude2md.py <conv.json> <out.md> <header>`: renders a claude.ai conversation export.
- `blind.py <repo> <scratch>/blind`: builds the shuffled anonymous candidate copies and the mapping.
- `prompts.py <repo> <scratch>`: writes the 24 `PROMPT.txt` files. The port and dialog-stub edits described in 3.2 and 3.3 were applied to the saved files afterwards.
- `finalize.py <repo> <scratch> {html|transcript|browser} [candidate-NN…]`: copies the reviews and renders the agent logs.
- `jsonl2md.py <session.jsonl> <out.md> <header>`: renders a Claude Code session log.
- `redact.py <session.jsonl> <private-terms.txt> <files…>`: redacts leaked personal strings in place.
