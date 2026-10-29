"""Per-judge blind inputs: judge/<judge>/<Letter>/{index.html,TRANSCRIPT.md}, CANDIDATES.md, and judge-mapping.json.

Each judge gets its own seeded shuffle onto letters A-H. Judge "browser" gets HTML copies whose native alert( calls
are rewritten to console.log( (it never sees code); every other HTML copy is byte-identical to its source.
Usage: judge_blind.py <repo> <out-dir>
"""
import hashlib, json, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blind import anonymize, candidates, VENDOR

JUDGES = {  # name: (seed, gets_html, gets_transcript, patch_alerts)
    "html":            (101, True,  False, False),
    "transcript":      (202, False, True,  False),
    "html_transcript": (303, True,  True,  False),
    "browser":         (404, True,  False, True),
    "browser_html":    (505, True,  False, False),
}
ALERT = re.compile(r"\balert\(")

def sha(b): return hashlib.sha256(b).hexdigest()

def main(R, OUT):
    names = candidates(R)
    mapping = {}
    for judge, (seed, html, tr, patch) in JUDGES.items():
        order = random.Random(seed).sample(names, len(names))
        rows, mapping[judge] = [], {}
        for letter, name in zip("ABCDEFGH", order):
            d = os.path.join(OUT, judge, letter); os.makedirs(d, exist_ok=True)
            src = os.path.join(R, name)
            version = "v" + name[-1]
            mapping[judge][letter] = {"name": name, "prompt": version}
            rows.append(f"| {letter} | {version} |")
            if html:
                f = [x for x in os.listdir(src) if x.endswith(".html")][0]
                data = open(os.path.join(src, f), "rb").read()
                if patch:
                    text, n = ALERT.subn("console.log(", data.decode("utf-8"))
                    mapping[judge][letter]["alerts_patched"] = n
                    data = text.encode("utf-8")
                else:
                    assert sha(data) == sha(open(os.path.join(src, f), "rb").read())
                open(os.path.join(d, "index.html"), "wb").write(data)
            if tr:
                t = anonymize(open(os.path.join(src, "TRANSCRIPTION.md")).read())
                assert not VENDOR.search(t), (judge, letter)
                open(os.path.join(d, "TRANSCRIPT.md"), "w").write(t)
        open(os.path.join(OUT, judge, "CANDIDATES.md"), "w").write(
            "# Candidates\n\n| Letter | Prompt version |\n|---|---|\n" + "\n".join(rows) + "\n")
    json.dump(mapping, open(os.path.join(OUT, "..", "judge-mapping.json"), "w"), indent=1)
    # self-checks: orders differ between judges, exactly the 2 known alert calls were patched
    orders = {tuple(v[l]["name"] for l in "ABCDEFGH") for v in mapping.values()}
    assert len(orders) == len(JUDGES), "two judges got the same order"
    patched = {v["name"]: v.get("alerts_patched", 0) for v in mapping["browser"].values()}
    assert sum(patched.values()) == 2 and patched["GitHub-CopilotTasks-Auto-Autopilot-v1"] == 2, patched
    return mapping

if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1], sys.argv[2]), indent=1))
