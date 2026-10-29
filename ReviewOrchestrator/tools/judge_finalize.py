"""Collect one judge: RANKING.md + screenshots into Judge/<Type>-Judge/, MAPPING.md, redacted TRANSCRIPT.md, and checks.
Usage: judge_finalize.py <repo> <scratch> <private-terms.txt> <judge>...
"""
import json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir
from judge_prompts import FOLDER, TITLE

P = os.path.expanduser("~/.claude/projects/-home-mpuchstein-Dev-AI-MandelbrotXR")
HERE = os.path.dirname(os.path.abspath(__file__))

def agent_log(name):
    for f in os.listdir(P):
        if f.endswith(".jsonl"):
            with open(os.path.join(P, f)) as fh:
                for line in fh:
                    found = json.loads(line).get("agentName")
                    if found:
                        if found == name: return os.path.join(P, f)
                        break
    raise SystemExit(f"no log for {name}")

def check_ranking(md):
    """Return a list of format problems (reported, never auto-fixed)."""
    problems = []
    sec = lambda h: (md.split(h, 1)[1].split("\n## ", 1)[0] if h in md else None)
    for h in ("## Ranking criteria", "## Ranking\n", "## Special elements", "## Summary of tests and approach"):
        if h not in md: problems.append(f"missing section {h.strip()}")
    table = sec("## Ranking\n") or ""
    rows = [r for r in table.splitlines() if r.startswith("|") and not re.match(r"^\|\s*-", r) and "Justification" not in r]
    letters = [re.sub(r"[^A-H]", "", r.split("|")[2]) for r in rows]
    if sorted(letters) != list("ABCDEFGH"): problems.append(f"ranking letters {letters}")
    for r in rows:
        n = len(r.split("|")[4].split())
        if n >= 50: problems.append(f"justification {r.split('|')[2].strip()} has {n} words")
    summary = sec("## Summary of tests and approach")
    if summary is not None and len(summary.split()) >= 200: problems.append(f"summary has {len(summary.split())} words")
    return problems, letters

def main(R, S, extra, judges):
    mapping = json.load(open(f"{S}/judge-mapping.json"))
    for judge in judges:
        dst, src = f"{R}/Judge/{FOLDER[judge]}", f"{S}/judge-out/{judge}"
        shutil.copyfile(f"{src}/RANKING.md", f"{dst}/RANKING.md")
        if os.path.isdir(f"{src}/screenshots"):
            shutil.copytree(f"{src}/screenshots", f"{dst}/screenshots", dirs_exist_ok=True)
        md = open(f"{dst}/RANKING.md").read()
        problems, order = check_ranking(md)
        m = mapping[judge]
        lines = [f"# {TITLE[judge]}: label mapping", "",
                 "Written by the orchestrator after the judge finished; the judge never saw this.", "",
                 "| Letter | Folder | Prompt | Judge's rank |", "|---|---|---|---|"]
        for l in "ABCDEFGH":
            rank = order.index(l) + 1 if l in order else "?"
            lines.append(f"| {l} | `{m[l]['name']}` | {m[l]['prompt']} | {rank} |")
        if judge == "browser":
            lines += ["", "Served copies: native `alert(` calls rewritten to `console.log(` (only the Autopilot candidate had any: 2 calls). All other files are byte-identical to the sources."]
        lines += ["", "## Format check", ""] + ([f"- {p}" for p in problems] or ["- all checks passed (8 letters once, justifications < 50 words, summary < 200 words)"])
        open(f"{dst}/MAPPING.md", "w").write("\n".join(lines) + "\n")
        log = agent_log(f"judge-{judge.replace('_', '-')}")
        hdr = (f"# Agent transcript: {FOLDER[judge]}\n\n"
               f"- Agent: `judge-{judge.replace('_', '-')}` (general-purpose subagent, Opus 5.5, effort high)\n"
               f"- Blind: letters A–H, own shuffle (see MAPPING.md)\n"
               f"- Rendered from the Claude Code session log. Tool inputs are cut at 4,000 characters and tool results at 2,000. System reminders are removed, and leaked personal strings are redacted.\n")
        subprocess.run([sys.executable, "-I", f"{HERE}/jsonl2md.py", log, f"{dst}/TRANSCRIPT.md", hdr], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([sys.executable, "-I", f"{HERE}/redact.py", log, extra, f"{dst}/TRANSCRIPT.md"], check=True, stdout=subprocess.DEVNULL)
        first = open(f"{dst}/TRANSCRIPT.md").read().split("### User", 1)[1].split("\n", 2)[2]
        prompt = open(f"{dst}/PROMPT.txt").read().strip()
        ok = first.strip().startswith(prompt[:300].strip()) and prompt[-200:].strip() in first
        print(judge, "prompt-match" if ok else "PROMPT MISMATCH", "| order:", "".join(order), "| problems:", problems or "none")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
