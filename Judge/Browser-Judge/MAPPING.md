# Browser Judge: label mapping

Written by the orchestrator after the judge finished; the judge never saw this.

| Letter | Folder | Prompt | Judge's rank |
|---|---|---|---|
| A | `Anthropic-Web-Opus5.5-Max-v1` | v1 | 4 |
| B | `GitHub-CopilotTasks-Auto-Interactive-v1` | v1 | 8 |
| C | `Anthropic-Web-Opus5.5-Max-v0` | v0 | 2 |
| D | `Google-Web-Gemini4Argon-High-v1` | v1 | 5 |
| E | `Mistral-VibeCode-MistralLarge4-Default-v1` | v1 | 6 |
| F | `GitHub-CopilotTasks-Auto-Autopilot-v1` | v1 | 7 |
| G | `OpenAI-Web-GPT6-Pro-v0` | v0 | 3 |
| H | `OpenAI-Web-GPT6-Pro-v1` | v1 | 1 |

Served copies: native `alert(` calls rewritten to `console.log(` (only the Autopilot candidate had any: 2 calls). All other files are byte-identical to the sources.

## Format check

- all checks passed (8 letters once, justifications < 50 words, summary < 200 words)
