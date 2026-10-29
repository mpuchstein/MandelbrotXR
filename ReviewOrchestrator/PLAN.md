# Plan: Extract 8 MandelbrotXR chats, then run a 24-agent blind review

## Context
The user had 8 web AI tools (ChatGPT, Claude, Mistral Vibe Code, Gemini Canvas, GitHub Copilot tasks) build a standalone WebXR Mandelbrot room HTML file from two prompt versions. The repo `/home/mpuchstein/Dev/AI/MandelbrotXR` (only an empty README, remote `git@github.com:mpuchstein/MandelbrotXR.git`) collects each result plus its chat transcript, then 3 kinds of review (HTML source, transcript, live browser) per result.

**Done when:** 8 extraction folders, each with its `.html` and `TRANSCRIPTION.md`, plus `prompt0.txt`/`prompt1.txt`, committed and pushed; `Review/{HTML,TRANSCRIPT,Browser}-Review/<name>/{REVIEW.md,TRANSCRIPT.md,PROMPT.txt}` × 8 = 24 sets; `ReviewOrchestrator/{PROMPT,TRANSCRIPT}.md`; second commit pushed.

## What the survey found (read-only)
| # | URL | Prompt | Provider/Tool/Model/Effort | Where the HTML is |
|---|-----|--------|-----------|------------|
| 1 | chatgpt …355ca | v0 | OpenAI-Web-GPT6-Pro (given by user) | file attachment `mandelbrot-room.html` (~630 KB) |
| 2 | claude.ai …09e85d21 | v0 | Anthropic-Web-Opus5.5-Max (composer chip; to confirm) | artifact "Mandelbrot room · Code · HTML" |
| 3 | claude.ai …0a5ff96f | v1 | Anthropic-Web-Opus5.5-Max (to confirm) | artifact "Mandelbrot xr" |
| 4 | chatgpt …356bd | v1 | ? (navigation blocked, will retry) | likely file attachment |
| 5 | mistral …/code/… | v1 | Mistral-VibeCode-?-? | in chat (`mistral-vibe-code-web/mandelbrot-xr.html`, code block) |
| 6 | gemini …bb0b8f | v1 | Google-Web-?-Hoch ("Argon · Hoch" in composer) | Canvas `index.html` (code view / Export) |
| 7 | github copilot task b471892c | v1 | GitHub-CopilotTasks-?-? | Artifacts panel (`/root/mandelbrot-xr.html`) |
| 8 | github copilot task 1976d0f6 | v1 | GitHub-CopilotTasks-?-? | Artifacts panel (`/root/mandelbrot-xr.html`) |

- prompt0 = ChatGPT v0 user message (three.js + three.xr.js version); prompt1 = Copilot user message (WebXR + "highest possible visual wow effect"). Both captured verbatim.
- Claude chat #3 has an unsent draft "Continuer" in its input box: do not touch it.
- Chrome extension site permission seems to be granted per visit (chatgpt.com refused on the 2nd visit), so the user may need to click "allow" for it.

## Steps

### 1. Extraction (I do this myself via Claude in Chrome, one chat at a time)
For each chat:
1. Read the model/effort from the message metadata, the model chip or a hover tooltip (ChatGPT "Thinking effort"/model slug, Copilot session info, Mistral session details, Gemini model menu).
2. Get the HTML: download the attachment (ChatGPT) and move it from `~/Downloads`; for Claude artifacts, Gemini Canvas, Copilot Artifacts and Mistral code blocks, read the source through `javascript_tool`/`get_page_text` and write it out exactly. Keep the provider's original filename. Check: the file starts with `<!doctype`/`<html` and ends with `</html>`, and its size is plausible.
3. TRANSCRIPTION.md = "everything visible": expand collapsed thinking / tool-call sections (without sending anything), then record User/Assistant turns, thinking and tool steps in Markdown. The full HTML body is not repeated; a pointer to the file is used instead.
4. **Confirmation gate:** before creating the folders, show the user the full list of 8 folder names (`{Provider}-{Tool}-{Model}-{Effort}-{v0|v1}`) and wait for an OK.
5. Write `prompt0.txt` and `prompt1.txt` to the repo root.

### 2. First commit + push
`git add -A && git commit -m "feat: add extracted MandelbrotXR outputs and transcripts"` (plain conventional commit, no trailer, per the user's CLAUDE.md), then `git push origin main`.

### 3. Review setup
- Create `Review/{HTML-Review,TRANSCRIPT-Review,Browser-Review}/<name>/` and `ReviewOrchestrator/`.
- **Blind copies** in the scratchpad: `/tmp/claude-1000/.../scratchpad/blind/candidate-NN/{index.html,TRANSCRIPT.md}`, NN shuffled. In the transcripts, speaker labels and product names (ChatGPT/Claude/Gemini/Copilot/Mistral/Vibe) are replaced by "Assistant"; the mapping is kept only in the orchestrator's notes. Caveat: the HTML/transcript text itself may still hint at the vendor, so the blinding is best effort.
- Shared rubric in every reviewer prompt: the matching prompt version (v0/v1 text), then 1–10 scores with justification for: meets "Done when", HMD/phone compatibility (Quest 3, Steam Frame, Pico 4 Ultra, Android, iOS), visual wow, usability/controls, code quality/robustness, plus a top-5 issues list and an overall score. The output is REVIEW.md written to the absolute target path.
- Each reviewer prompt gets saved verbatim to `<target>/PROMPT.txt` before its launch.

### 4. HTML + transcript reviews (16 agents, parallel)
`Agent(subagent_type="general-purpose", model="opus", effort="xhigh")`, all in one message. HTML reviewers may read only their `candidate-NN/index.html`; transcript reviewers only their `candidate-NN/TRANSCRIPT.md`. They may not open a browser or look at other candidates.

### 5. Browser reviews (8 agents, sequential)
For each candidate in turn:
1. Start `python3 -m http.server 8765 --bind 127.0.0.1 -d <scratchpad>/blind/candidate-NN` (in the background).
2. Start one `general-purpose`/opus/xhigh agent: it opens `http://localhost:8765/` in a new Claude in Chrome tab, checks rendering, console errors and controls, uses Chrome's mobile viewport if available, tries Enter VR/AR (if available; no XR emulator required), takes screenshots, writes REVIEW.md and closes its tab.
3. Wait for it to finish, stop the server, continue with the next one.

### 6. Saving agent transcripts
Subagent JSONL logs are in `~/.claude/projects/-home-mpuchstein-Dev-AI-MandelbrotXR/14a78f0a-…/subagents/` (I verify the path after the first launch). A small converter `scratchpad/jsonl2md.py` (stdlib, run with `python3 -I`) turns each one into TRANSCRIPT.md (user/assistant text, thinking, tool calls + truncated results), with the agentId → folder mapping taken from the Agent results. The same script converts this session's `14a78f0a-….jsonl` into `ReviewOrchestrator/TRANSCRIPT.md`; `ReviewOrchestrator/PROMPT.md` = the user's original message verbatim. The orchestrator transcript is generated as the last step before the commit, so it ends there.

### 7. Second commit + push
`git add Review ReviewOrchestrator && git commit -m "docs: add blind reviews of MandelbrotXR outputs" && git push`.

## Verification
- `find . -name '*.html' -path '*-v?/*'` → 8 files, each ends with `</html>`; 8 TRANSCRIPTION.md files.
- `find Review -name REVIEW.md | wc -l` = 24, same for TRANSCRIPT.md and PROMPT.txt.
- `git log --oneline` shows 2 new commits; `git status` is clean; `git ls-remote origin main` = local HEAD.
- Spot check: open one REVIEW.md per review type and one converted TRANSCRIPT.md.

## Risks / user interaction
- Chrome site-permission prompts (chatgpt.com, localhost) need a click from the user.
- Downloading the ChatGPT attachments counts as a file download that the request already approved.
- 24 opus/xhigh agents are expensive (7d quota at 96%); `ai-quota --brief --for claude --fresh` gets checked before step 4.
