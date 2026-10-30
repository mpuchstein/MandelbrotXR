# MandelbrotXR

Five AI assistants (Claude, ChatGPT, Gemini, Mistral and GitHub Copilot) were asked for a standalone HTML page
that puts the Mandelbrot set in a virtual room you can enter with a VR headset, AR glasses or a phone. Eight
chats produced eight pages. Blind agents reviewed each page from its HTML, its chat transcript and in the
browser, then five blind judges ranked all eight.

The results site lets you sort the rankings, read every review and judgment, and play each page:
**<https://mandelbrotxr.puchstein.dev>**

## Result

Mean rank across the five judges (1 = best), from [Judge/README.md](Judge/README.md), which also lists each
judge's ranks:

| Folder | Prompt | Mean rank |
|---|---|---|
| [`Anthropic-Web-Opus5.5-Max-v1`](Anthropic-Web-Opus5.5-Max-v1/) | v1 | 1.8 |
| [`Anthropic-Web-Opus5.5-Max-v0`](Anthropic-Web-Opus5.5-Max-v0/) | v0 | 1.8 |
| [`OpenAI-Web-GPT6-Pro-v1`](OpenAI-Web-GPT6-Pro-v1/) | v1 | 3.0 |
| [`OpenAI-Web-GPT6-Pro-v0`](OpenAI-Web-GPT6-Pro-v0/) | v0 | 3.4 |
| [`Google-Web-Gemini4Argon-High-v1`](Google-Web-Gemini4Argon-High-v1/) | v1 | 5.6 |
| [`Mistral-VibeCode-MistralLarge4-Default-v1`](Mistral-VibeCode-MistralLarge4-Default-v1/) | v1 | 5.8 |
| [`GitHub-CopilotTasks-Auto-Autopilot-v1`](GitHub-CopilotTasks-Auto-Autopilot-v1/) | v1 | 6.8 |
| [`GitHub-CopilotTasks-Auto-Interactive-v1`](GitHub-CopilotTasks-Auto-Interactive-v1/) | v1 | 7.8 |

The two Opus builds tie. The judges' agreement, as Judge/README.md puts it:

> - **Top four:** the two Opus 5.5 builds, then the two GPT6 Pro builds, in every judge's list.
> - **Bottom two:** the two Copilot builds, in every list except the transcript judge's.
> - **Exceptions:**
>   - The **browser judge** put GPT6-Pro-v1 first and Opus-v1 fourth, based on what a desktop user sees first: the room's polish and the XR-info dialog.
>   - The **transcript judge** put Gemini last, because it shipped a shader that failed to compile and was never verified.

The phase-1 review scores (1–10, per review type) are in [ReviewOrchestrator/README.md](ReviewOrchestrator/README.md) §4.

## Caveats

- The prompts differ. [prompt0.txt](prompt0.txt) (v0) asks for three.js and three.xr.js; [prompt1.txt](prompt1.txt)
  (v1) asks for WebXR and "the highest possible visual wow effect and good usability". Each page was judged
  against its own prompt, in one combined ranking.
- No real VR or AR session was entered. Everything was tested in desktop Chrome, without an XR device or emulator.
- All reviewers and judges were Opus 5.5 agents, and two of the eight pages are Opus 5.5 builds.

Deviations and incidents, such as the effort setting, a rerun browser review, a blocking `alert()` and a privacy
rewrite, are in [ReviewOrchestrator/README.md](ReviewOrchestrator/README.md) §3 and [Judge/README.md](Judge/README.md).

## Repository layout

```
<Vendor>-<Product>-<Model>-<Effort>-v<N>/   one per chat: the page (HTML) and TRANSCRIPTION.md
prompt0.txt, prompt1.txt                    the two task prompts, verbatim
Review/                                     phase 1: 24 blind reviews (HTML, transcript, browser)
Judge/                                      phase 2: 5 blind rankings and their aggregate
ReviewOrchestrator/                         how it was run: plan, prompts, session log, incidents, tools
site/                                       generator for the results site
```

## Build the site

Standard library only, Python 3.12 or newer, from the repository root:

```bash
python3 -I site/build.py        # writes site/dist/
python3 -I site/test_build.py   # checks the data, links, determinism and extensibility
```

[site/README.md](site/README.md) covers the data model and how to add a judgment, and [site/DEPLOY.md](site/DEPLOY.md)
the hosting notes. A Claude Code cloud session built the generator from [site/BRIEF.md](site/BRIEF.md) and
[site/BRIEF-ADDENDUM.md](site/BRIEF-ADDENDUM.md).
