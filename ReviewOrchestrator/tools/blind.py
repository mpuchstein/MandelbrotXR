"""Build anonymized candidate copies: blind/candidate-NN/{index.html,TRANSCRIPT.md}; writes blind/mapping.json."""
import json, os, random, re, shutil, sys

R, OUT = sys.argv[1], sys.argv[2]
names = sorted(d for d in os.listdir(R) if re.search(r"-v[01]$", d))
assert len(names) == 8, names
random.seed(20261029)
order = random.sample(names, len(names))

SUBS = [
    (r"Gemini hat gesagt", "Assistant said"), (r"ChatGPT said:", "Assistant said:"),
    (r"ChatGPT can make mistakes\.[^\n]*", ""),
    (r"mistral-vibe-code-web", "assistant-output"),
    (r"gpt-5\.6-luna|GPT-?6(\.\d)?( Pro)?|claude-opus-5-5|Opus 5\.5|Gemini 4 Argon|4 Argon|Mistral Large 4", "[model]"),
    (r"Claude\.ai|claude\.ai|ChatGPT|Claude|Anthropic|OpenAI|Gemini|Mistral|Le Chat|GitHub Copilot|Copilot|Vibe", "[assistant]"),
]

def anonymize(md):
    body = md.split("\n---\n", 1)[1]  # drop identifying header block
    for pat, rep in SUBS:
        body = re.sub(pat, rep, body)
    return "# Chat transcript (anonymized)\n\nProduct, model and vendor names are replaced with [assistant]/[model]. The HTML deliverable is reviewed separately.\n\n---\n" + body

mapping = {}
for i, name in enumerate(order, 1):
    cid = f"candidate-{i:02d}"
    d = os.path.join(OUT, cid); os.makedirs(d, exist_ok=True)
    src = os.path.join(R, name)
    html = [f for f in os.listdir(src) if f.endswith(".html")]
    assert len(html) == 1, (name, html)
    shutil.copyfile(os.path.join(src, html[0]), os.path.join(d, "index.html"))
    with open(os.path.join(src, "TRANSCRIPTION.md")) as f: t = anonymize(f.read())
    with open(os.path.join(d, "TRANSCRIPT.md"), "w") as f: f.write(t)
    mapping[cid] = {"name": name, "prompt": "prompt" + name[-1] + ".txt", "original_html": html[0]}
with open(os.path.join(OUT, "..", "blind-mapping.json"), "w") as f: json.dump(mapping, f, indent=1)
# self-check: no vendor names left in transcripts
for cid in mapping:
    t = open(os.path.join(OUT, cid, "TRANSCRIPT.md")).read()
    assert not re.search(r"ChatGPT|Claude|Gemini|Copilot|Mistral|OpenAI|Anthropic", t), cid
print(json.dumps(mapping, indent=1))
