"""Extract the messages the user typed in a Claude Code session log into Markdown (verbatim, in order, deduplicated).
Usage: user_prompts.py <session.jsonl> <out.md>
"""
import json, re, sys

SKIP = ("<teammate-message", "<cross-session", "<task-notification", "[Request interrupted", "Another Claude session sent a message:")

def prompts(src):
    seen_uuid, seen_text = set(), set()
    for line in open(src):
        d = json.loads(line)
        if d.get("type") != "user" or d.get("isMeta") or d.get("uuid") in seen_uuid: continue
        seen_uuid.add(d.get("uuid"))
        c = d["message"]["content"]
        for t in ([c] if isinstance(c, str) else [b.get("text", "") for b in c if b.get("type") == "text"]):
            t = re.sub(r"<system-reminder>.*?</system-reminder>", "", t, flags=re.S).strip()
            if not t or t.startswith(SKIP) or t in seen_text: continue
            seen_text.add(t)
            yield d.get("timestamp", ""), t

if __name__ == "__main__":
    out = ["# User prompts of the orchestrator session", "",
           "Every message the user typed in this session, verbatim and in order. Teammate messages, tool results and question-dialog answers are excluded; the answers are in TRANSCRIPT.md.",
           "Prompt 1 is an earlier, line-wrapped and truncated copy of Prompt 2 that the session log also recorded; it is kept as logged.", ""]
    ps = list(prompts(sys.argv[1]))
    for i, (ts, t) in enumerate(ps, 1):
        out += [f"## Prompt {i} · {ts}", "", "````", t, "````", ""]
    open(sys.argv[2], "w").write("\n".join(out))
    assert ps and not any(t.startswith(SKIP) for _, t in ps)
    print(len(ps), "prompts")
