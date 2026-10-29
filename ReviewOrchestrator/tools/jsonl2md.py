"""Render a Claude Code session JSONL (main session or teammate) as a Markdown transcript."""
import json, re, sys

IN_MAX, OUT_MAX = 4000, 2000

def clip(s, n):
    return s if len(s) <= n else s[:n] + f"\n… [truncated, {len(s) - n} more chars]"

def fence(s):
    return "````\n" + s.replace("````", "` ` ` `") + "\n````"

def strip_wrappers(t):
    t = re.sub(r"<system-reminder>.*?</system-reminder>", "", t, flags=re.S)
    m = re.match(r'\s*<teammate-message[^>]*>\n?(.*?)\n?</teammate-message>\s*$', t, flags=re.S)
    return (m.group(1) if m else t).strip()

def result_text(c):
    if isinstance(c, str): return c
    out = []
    for p in c or []:
        if p.get("type") == "text": out.append(p["text"])
        elif p.get("type") == "image": out.append("[image]")
        else: out.append(f"[{p.get('type')}]")
    return "\n".join(out)

def render(path, header):
    out = [header, ""]
    seen = set()
    for line in open(path):
        d = json.loads(line)
        if d.get("type") not in ("user", "assistant") or d.get("isMeta"): continue
        if d.get("uuid") in seen: continue
        seen.add(d.get("uuid"))
        msg = d.get("message") or {}
        role, content = msg.get("role"), msg.get("content")
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else (content or [])
        parts = []
        for b in blocks:
            t = b.get("type")
            if t == "text":
                txt = strip_wrappers(b["text"]) if role == "user" else b["text"].strip()
                if txt: parts.append(txt)
            elif t == "thinking":
                if b.get("thinking", "").strip():
                    parts.append("<details><summary>Thinking</summary>\n\n" + b["thinking"].strip() + "\n\n</details>")
            elif t == "tool_use":
                parts.append(f"**Tool call `{b['name']}`**\n" + fence(clip(json.dumps(b.get("input"), ensure_ascii=False, indent=1), IN_MAX)))
            elif t == "tool_result":
                parts.append(f"<details><summary>Tool result{' (error)' if b.get('is_error') else ''}</summary>\n\n" + fence(clip(result_text(b.get("content")), OUT_MAX)) + "\n\n</details>")
        if not parts: continue
        label = "Assistant" if role == "assistant" else ("Tool output" if all(p.startswith("<details><summary>Tool result") for p in parts) else "User")
        out.append(f"### {label} · {d.get('timestamp', '')}\n")
        out.extend(p + "\n" for p in parts)
    return "\n".join(out)

if __name__ == "__main__":
    src, dst, header = sys.argv[1:4]
    md = render(src, header)
    open(dst, "w").write(md)
    assert "### " in md, "no messages rendered"
    print(dst, len(md))
