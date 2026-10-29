"""Copy blind reviews into Review/<Type>-Review/<name>/ and render each agent's session log as TRANSCRIPT.md."""
import json, os, shutil, subprocess, sys
R, S, kind = sys.argv[1], sys.argv[2], sys.argv[3]   # kind: html | transcript | browser
only = sys.argv[4:] or None
P = os.path.expanduser("~/.claude/projects/-home-mpuchstein-Dev-AI-MandelbrotXR")
folder = {"html": "HTML-Review", "transcript": "TRANSCRIPT-Review", "browser": "Browser-Review"}[kind]
mapping = json.load(open(f"{S}/blind-mapping.json"))
logs = {}
for f in os.listdir(P):
    if not f.endswith(".jsonl"): continue
    with open(os.path.join(P, f)) as fh:
        for line in fh:
            name = json.loads(line).get("agentName")
            if name: logs[name] = os.path.join(P, f); break
for cid, m in sorted(mapping.items()):
    if only and cid not in only: continue
    agent = f"{kind}-c{cid[-2:]}"
    if f"{agent}-rerun" in logs: agent = f"{agent}-rerun"  # browser-c02 first run saw a cached page from candidate-01
    dst = f"{R}/Review/{folder}/{m['name']}"
    src = f"{S}/blind-out/{kind}/{cid}"
    shutil.copyfile(f"{src}/REVIEW.md", f"{dst}/REVIEW.md")
    if os.path.isdir(f"{src}/screenshots"):
        shutil.copytree(f"{src}/screenshots", f"{dst}/screenshots", dirs_exist_ok=True)
    hdr = (f"# Agent transcript: {folder} / {m['name']}\n\n"
           f"- Agent: `{agent}` (general-purpose subagent, Opus; requested effort xhigh, but the API requests show effort `high`)\n"
           f"- Reviewed blind as `{cid}`; the vendor/model mapping was applied afterwards by the orchestrator\n"
           f"- Rendered from the Claude Code session log. Tool inputs are cut at 4,000 characters and tool results at 2,000. System reminders are removed.\n")
    subprocess.run([sys.executable, "-I", f"{S}/tools/jsonl2md.py", logs[agent], f"{dst}/TRANSCRIPT.md", hdr], check=True)
    # prompt check: the first user message must equal PROMPT.txt
    first = open(f"{dst}/TRANSCRIPT.md").read().split("### User", 1)[1].split("\n", 2)[2]
    prompt = open(f"{dst}/PROMPT.txt").read().strip()
    print(cid, agent, "prompt-match" if first.strip().startswith(prompt[:-40].strip()) and prompt[-60:].strip() in first else "PROMPT MISMATCH")
