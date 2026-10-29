"""Collect personal strings that leaked into a session log through page dumps / directory listings, and redact them.

Sources: the Gemini page text (sidebar chat titles, location) and `ls ~/Downloads` listings.
Usage: redact.py <session.jsonl> <private-terms.txt> <file.md>...   (rewrites files in place; exits 1 if a term survives)
"""
import json, os, re, sys

OURS = re.compile(r"^(mandelbrot-room\.html|mandelbrot-xr\.html|root_mandelbrot-xr\.html|holographic_3d_mandelbrot_webxr_sanctuary\.html|claude-conv-.*\.json|mistral-.*)$")

def walk_strings(o):
    if isinstance(o, str): yield o
    elif isinstance(o, dict):
        for v in o.values(): yield from walk_strings(v)
    elif isinstance(o, list):
        for v in o: yield from walk_strings(v)

def collect_terms(jsonl, own_roots=()):
    terms = set()
    for line in open(jsonl):
        for s in walk_strings(json.loads(line)):
            # Gemini sidebar: lines between the "Alle" heading and "Aktivitäten"
            if s.startswith("Title:") and "Unterhaltung mit Gemini" in s:
                block = s.split("\nAlle\n", 1)[-1].split("\nAktivitäten", 1)[0]
                terms.update(l.strip() for l in block.split("\n") if len(l.strip()) >= 6)
                # the two lines after "Aktivitäten" are the location widget
                terms.update(l.strip() for l in s.split("\nAktivitäten\n", 1)[-1].split("\n")[:2] if len(l.strip()) >= 6)
            # ls -l listings of ~/Downloads: keep only files this run created
            for m in re.finditer(r"^[-d][rwx-]{9} +\d+ +\S+ +\S+ +\d+ +\d+\. \S+ +[\d:]+ (.+)$", s, flags=re.M):
                name = m.group(1).strip()
                if len(name) >= 6 and not OURS.match(name) and not name.startswith("mistral-page"):
                    terms.add(name)
    # the run's own subject matter and files this run created must never be redacted
    import os
    own = set()
    for root in ("/home/mpuchstein/Dev/AI/MandelbrotXR", *own_roots):
        for _, dirs, files in os.walk(root):
            own.update(dirs); own.update(files)
    terms = {t for t in terms if t not in own and not re.search(r"Create a standalone html file|Mandelbrot", t)}
    return sorted(terms, key=len, reverse=True)

def extra_terms(path):
    # private list (not committed): quoted fragments and probe strings, one per line
    return [l.strip() for l in open(path) if l.strip()] if path else []

if __name__ == "__main__":
    jsonl, extra, files = sys.argv[1], sys.argv[2], sys.argv[3:]
    terms = sorted(set(collect_terms(jsonl, own_roots=[os.path.dirname(os.path.abspath(extra))])) | set(extra_terms(extra)), key=len, reverse=True)
    print(f"{len(terms)} terms")
    bad = 0
    for f in files:
        t = open(f).read()
        for term in terms:
            t = t.replace(term, "[redacted]")
        open(f, "w").write(t)
        for probe in terms:
            if probe in t: print("SURVIVED", probe, "in", f); bad = 1
    sys.exit(bad)
