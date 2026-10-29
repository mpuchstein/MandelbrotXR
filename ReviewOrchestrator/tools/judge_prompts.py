"""Write the 5 judge prompts to Judge/<Type>-Judge/PROMPT.txt (blind: they reference only letters and scratch paths).
Usage: judge_prompts.py <repo> <scratch>
"""
import os, sys

FOLDER = {"html": "HTML-Judge", "transcript": "TRANSCRIPT-Judge", "html_transcript": "HTML_TRANSCRIPT-Judge",
          "browser": "Browser-Judge", "browser_html": "Browser_HTML-Judge"}
PORT_BASE = {"browser": 8800, "browser_html": 8900}

HEAD = """You are a blind judge in a comparison of AI coding assistants. Eight assistants each built a standalone HTML file from one of two prompt versions. They are labelled A–H in random order. You do not know which assistant or model made which candidate: don't guess and don't mention vendors or models.

Prompt v0 (verbatim):
<<<
{p0}>>>

Prompt v1 (verbatim):
<<<
{p1}>>>

Which prompt each candidate answered is listed in {inp}/CANDIDATES.md. Produce ONE combined ranking of all 8, best to worst, and judge each candidate against its own prompt version: a v0 candidate isn't penalised for missing the v1 "wow" goal, and a v1 candidate isn't held to v0's three.js requirement.

Your material is ONLY what is under {inp}/ (and, for browser work, the localhost URLs below). Do NOT read any other file or directory: no repositories, no other judges' folders, nothing else in the scratchpad.
"""

TASK = {
"html": """
Your task: HTML judge. Each candidate is one file, {inp}/<Letter>/index.html. Review the source statically: read it (in parts if large), grep it, and you may run read-only checks such as extracting inline scripts and running `node --check`. Do NOT open the files in a browser or start servers. Several files embed a bundled library such as three.js; skim that, and spend your effort on the application code.
Special elements to highlight: features that only one or a few candidates have, and libraries or techniques that no one else uses.
""",
"transcript": """
Your task: transcript judge. Each candidate is one anonymized chat transcript of the assistant's work session, {inp}/<Letter>/TRANSCRIPT.md. Product names are replaced by [assistant]/[model], and the HTML deliverable itself is not included. Judge the work session: understanding of the requirements, process, verification, honesty and handoff.
Special elements to highlight: unusually good explanations of what was built, the reasoning given for decisions, and hallucinations or overclaims (claims the transcript doesn't back up).
""",
"html_transcript": """
Your task: HTML + transcript judge. Each candidate has {inp}/<Letter>/index.html (the deliverable) and {inp}/<Letter>/TRANSCRIPT.md (the anonymized work session). Do static review only: no browser, no servers. Several files embed a bundled library such as three.js; skim that, and focus on the application code. Cross-check the transcript's claims against the code.
Special elements to highlight: special features, where a candidate departs from what most of the others did, and claims in the transcript that the code doesn't support.
""",
"browser": """
Your task: browser judge. Test the 8 products hands-on in Chrome. You must NOT read any source code. All 8 are served right now, each on its own origin:
{urls}
Note: native alert() calls in these served copies were rewritten to console.log() before serving, so any such messages show up in the console (read_console_messages) instead of as blocking dialogs. If you see one, treat it as the product having used a native dialog there.
""",
"browser_html": """
Your task: browser + HTML judge. Test the 8 products hands-on in Chrome AND read their source to explain what you observe. The source is {inp}/<Letter>/index.html (several embed a bundled library such as three.js; skim that). All 8 are served right now, each on its own origin:
{urls}
Native dialogs: before testing a candidate, grep its source for `alert(`, `confirm(` and `prompt(`. Native dialogs block the browser extension. So right after every page load (and after every reload), switch them to console output in javascript_tool: `window.alert = m => console.log('ALERT: ' + m); window.confirm = m => (console.log('CONFIRM: ' + m), false); window.prompt = m => (console.log('PROMPT: ' + m), null);`, and read the messages with read_console_messages. Count a candidate's use of native dialogs as a finding.
Special elements to highlight: how specific code decisions (rendering technique, libraries, XR session setup, input handling, fallbacks, performance work) shaped the result you observed.
""",
}

BROWSER_RULES = """
Browser rules: use the Claude in Chrome tools (mcp__claude-in-chrome__*). If they are deferred, load them with ONE ToolSearch call, e.g. "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__read_console_messages,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__resize_window".
- Call tabs_context_mcp first, then create your OWN tab(s) and close them all when done. Visit no URLs other than the ones listed above.
- For each candidate: load it, read the console, use its controls (start buttons, presets, menus, orbit/zoom, keyboard), check its Enter VR/AR behaviour on this desktop without an XR device, and try a phone-like width.
- Known limits of this environment: the window manager may refuse to resize below about 446 px, Chrome may throttle frame rate in the background, and there is no WebXR emulator, so no real XR session can be entered. Note these limits; don't score candidates on them.
- Save up to 16 key screenshots (save_to_disk) and copy them into {out}/screenshots/ named <Letter>-<what>.jpg. Use screenshot scale ≤ 0.6 to save context.
"""

OUTPUT = """
Output: write Markdown to exactly {out}/RANKING.md (create the directory if needed), with these sections in this order:
1. "## Ranking criteria": the criteria you ranked by (weights optional), each with a one-line rationale.
2. "## Ranking": a table, best to worst, with the columns Rank | Candidate | Prompt | Justification. Every letter A–H appears exactly once. Each justification is UNDER 50 words.
3. "## Special elements": a list. Each item names the candidate letter(s) and the element, followed by exactly ONE sentence explaining why you selected it.
4. "## Summary of tests and approach": UNDER 200 words on what you did and how.
Start the file with "# {title} — blind ranking". Write no other files except where stated above. Finish by replying with a 3-line summary: winner, last place, most notable special element.
"""

TITLE = {"html": "HTML Judge", "transcript": "Transcript Judge", "html_transcript": "HTML + Transcript Judge",
         "browser": "Browser Judge", "browser_html": "Browser + HTML Judge"}

def build(R, S, judge):
    inp, out = f"{S}/judge/{judge}", f"{S}/judge-out/{judge}"
    urls = ""
    if judge in PORT_BASE:
        urls = "\n".join(f"  {l}: http://localhost:{PORT_BASE[judge] + i}/" for i, l in enumerate("ABCDEFGH", 1))
    p0, p1 = open(f"{R}/prompt0.txt").read(), open(f"{R}/prompt1.txt").read()
    text = HEAD.format(p0=p0, p1=p1, inp=inp) + TASK[judge].format(inp=inp, urls=urls)
    if judge in PORT_BASE:
        text += BROWSER_RULES.format(out=out)
    text += OUTPUT.format(out=out, title=TITLE[judge])
    return text

if __name__ == "__main__":
    R, S = sys.argv[1], sys.argv[2]
    for judge, folder in FOLDER.items():
        d = f"{R}/Judge/{folder}"; os.makedirs(d, exist_ok=True)
        os.makedirs(f"{S}/judge-out/{judge}", exist_ok=True)
        text = build(R, S, judge)
        open(f"{d}/PROMPT.txt", "w").write(text)
        print(folder, len(text.split()), "words")
