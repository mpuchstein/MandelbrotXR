"""Render a claude.ai conversation JSON (tree=True, rendering_mode=messages) as Markdown."""
import json, sys

IN_MAX, OUT_MAX = 3000, 1500

def clip(s, n):
    s = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False, indent=1)
    return s if len(s) <= n else s[:n] + f"\n… [truncated, {len(s) - n} more chars]"

def fence(s):
    return "````\n" + s.replace("````", "` ` ` `") + "\n````"

def result_text(x):
    parts = []
    for c in x.get("content") or []:
        if c.get("type") == "text": parts.append(c["text"])
        elif c.get("type") == "image": parts.append("[image]")
        elif c.get("type") == "knowledge": parts.append(f"- {c.get('title')} <{c.get('url')}>")
        else: parts.append(f"[{c.get('type')}]")
    return "\n".join(parts)

def render(conv, header):
    out = [header, ""]
    for m in conv["chat_messages"]:
        out.append("---\n")
        out.append(f"## {'User' if m['sender'] == 'human' else 'Assistant'} (message {m['index']}, {m['created_at']})\n")
        for x in m["content"]:
            t = x["type"]
            if t == "text":
                out.append(x["text"] + "\n")
            elif t == "thinking":
                sums = [s["summary"] for s in x.get("summaries") or []]
                body = x.get("thinking") or ""
                out.append("<details><summary>Thinking</summary>\n")
                out.extend(f"- {s}" for s in sums)
                if body: out.append("\n" + body)
                out.append("\n</details>\n")
            elif t == "tool_use":
                inp = dict(x.get("input") or {})
                desc = inp.pop("description", "")
                for k in ("file_text", "content", "new_str", "old_str"):
                    if k in inp and isinstance(inp[k], str) and len(inp[k]) > IN_MAX:
                        inp[k] = clip(inp[k], IN_MAX)
                out.append(f"**Tool call `{x['name']}`**{': ' + desc if desc else ''}\n")
                out.append(fence(clip(json.dumps(inp, ensure_ascii=False, indent=1), IN_MAX * 2)) + "\n")
            elif t == "tool_result":
                out.append(f"<details><summary>Tool result `{x.get('name')}`{' (error)' if x.get('is_error') else ''}</summary>\n")
                out.append(fence(clip(result_text(x), OUT_MAX)) + "\n</details>\n")
            else:
                out.append(f"[{t} block]\n")
    return "\n".join(out)

if __name__ == "__main__":
    src, dst, header = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(src) as f: conv = json.load(f)
    with open(dst, "w") as f: f.write(render(conv, header))
    # self-check: every message index rendered once
    text = open(dst).read()
    assert all(f"(message {m['index']}," in text for m in conv["chat_messages"])
