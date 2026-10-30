"""Build-time full-text search index for the static site (client: assets/js/search.js).

Normalisation, shared with search.js (keep in sync):
  1. Unicode NFKD, then drop every combining mark (general category M*).
  2. Casefold (JS: toLowerCase() plus ß->ss and ς->σ, which covers casefold for this corpus).
  3. Split on anything that is not a letter or number (Python [^\\W_]+, JS [\\p{L}\\p{N}]+).
  4. Keep tokens of >= 2 code points, plus pure ASCII-digit numbers of any length.
  5. Drop STOPWORDS (also shipped in meta.json as "stop").

Output files in out_dir:
  meta.json   {"v","kinds","n","shards","docshards","docshard_size","stop"}
              shards maps a term prefix to an index file; a term lives under the
              longest prefix key it starts with (keys are 2 chars, longer when split).
  p.json      {"docs": [[url, title, kind, context, first_passage_id], ...],
               "len": [token count per passage],
               "same": [[passage id, id of the first passage with identical text], ...]}
              (ranking, filtering and merging duplicate passages without text)
  i-<k>.json  {term: postings}; postings = base36 passage-id deltas joined by ","
              with ":<tf in base36>" appended when tf > 1.
  d-<k>.json  [[url, title, kind, context, text], ...] for passage ids
              k*docshard_size .. (k+1)*docshard_size-1.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata

STOPWORDS = (
    "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has", "have",
    "he", "her", "his", "if", "in", "into", "is", "it", "its", "no", "not", "of", "on",
    "or", "our", "she", "so", "such", "than", "that", "the", "their", "them", "then",
    "there", "these", "they", "this", "to", "was", "we", "were", "which", "will",
    "with", "you", "your",
)
_STOP = frozenset(STOPWORDS)
_WORD = re.compile(r"[^\W_]+")
_DIGITS = re.compile(r"[0-9]+")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_PARA = re.compile(r"\n\s*\n")

MIN_PASSAGE, MAX_PASSAGE = 500, 900
INDEX_TARGET, INDEX_MAX = 64_000, 150_000
DOC_TARGET = 100_000
_JSON = {"ensure_ascii": False, "separators": (",", ":"), "sort_keys": True}


def tokenize(text: str) -> list[str]:
    """Return the index terms of ``text`` (see module docstring)."""
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.category(c).startswith("M")).casefold()
    return [t for t in _WORD.findall(s)
            if (len(t) >= 2 or _DIGITS.fullmatch(t)) and t not in _STOP]


def _b36(n: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        n, r = divmod(n, 36)
        out = digits[r] + out
        if not n:
            return out


def _hard_split(s: str, limit: int) -> list[str]:
    """Split an over-long sentence at the last space before ``limit``."""
    out = []
    while len(s) > limit:
        cut = s.rfind(" ", limit // 2, limit)
        cut = cut if cut > 0 else limit
        out.append(s[:cut].strip())
        s = s[cut:].strip()
    return out + ([s] if s else [])


def split_passages(text: str) -> list[str]:
    """Split text into ~MIN..MAX character passages on paragraph/sentence boundaries."""
    units: list[str] = []
    for para in _PARA.split(text):
        para = " ".join(para.split())
        if not para:
            continue
        if len(para) <= MAX_PASSAGE:
            units.append(para)
            continue
        chunk = ""
        for sent in _SENTENCE.split(para):
            for piece in _hard_split(sent, MAX_PASSAGE):
                if chunk and len(chunk) + 1 + len(piece) > MAX_PASSAGE:
                    units.append(chunk)
                    chunk = piece
                else:
                    chunk = f"{chunk} {piece}" if chunk else piece
        if chunk:
            units.append(chunk)
    passages: list[str] = []
    cur = ""
    for u in units:
        if cur and len(cur) < MIN_PASSAGE and len(cur) + 1 + len(u) > MAX_PASSAGE:
            # Top up a short passage (often a heading) with leading sentences of u;
            # if nothing fits, keep it attached to u rather than orphaned.
            sents, sep = _SENTENCE.split(u), "\n"
            while len(sents) > 1 and len(cur) + 1 + len(sents[0]) <= MAX_PASSAGE:
                cur, sep = cur + sep + sents.pop(0), " "
            u = " ".join(sents)
            if len(cur) < MIN_PASSAGE // 2:
                cur, u = "", cur + sep + u
        if cur and (len(cur) >= MIN_PASSAGE or len(cur) + 1 + len(u) > MAX_PASSAGE):
            passages.append(cur)
            cur = u
        else:
            cur = f"{cur}\n{u}" if cur else u
    if cur:
        if passages and len(cur) < MIN_PASSAGE // 2 and len(passages[-1]) + len(cur) < MAX_PASSAGE + MIN_PASSAGE // 2:
            passages[-1] += "\n" + cur
        else:
            passages.append(cur)
    return passages or [""]


def _dump(obj: object) -> bytes:
    return json.dumps(obj, **_JSON).encode("utf-8")


def _shard_keys(sizes: dict[str, int]) -> dict[str, str]:
    """Map each term to its prefix key, lengthening keys of over-large groups."""
    keys = {t[:2] for t in sizes}
    while True:
        assign: dict[str, str] = {}
        for t in sizes:
            k = t[:2]
            while t[:len(k) + 1] in keys and len(k) < len(t):
                k = t[:len(k) + 1]
            assign[t] = k
        totals: dict[str, int] = {}
        for t, k in assign.items():
            totals[k] = totals.get(k, 0) + sizes[t]
        new = {t[:len(k) + 1] for t, k in assign.items()
               if totals[k] > INDEX_MAX and len(t) > len(k) and len(k) < 8}
        if new <= keys:
            return assign
        keys |= new


def _pack(items: list[tuple[str, int]], target: int, limit: int) -> list[list[str]]:
    """Greedily group consecutive (name, size) items into files near ``target`` bytes."""
    groups: list[list[str]] = []
    sizes: list[int] = []
    for name, size in items:
        if groups and sizes[-1] + size <= target:
            groups[-1].append(name)
            sizes[-1] += size
        else:
            groups.append([name])
            sizes.append(size)
    if len(groups) > 1 and sizes[-1] < target // 4 and sizes[-1] + sizes[-2] <= limit:
        groups[-2] += groups.pop()
    return groups


def build(docs: list[dict], out_dir: str) -> dict:
    """Write the search index for ``docs`` into ``out_dir``; return size stats."""
    order = sorted(docs, key=lambda d: (d["url"], d["title"], d["kind"], d["context"], d["text"]))
    table: list[list] = []
    passages: list[list[str]] = []
    lengths: list[int] = []
    postings: dict[str, list[tuple[int, int]]] = {}
    for d in order:
        table.append([d["url"], d["title"], d["kind"], d["context"], len(passages)])
        for text in split_passages(d["text"]):
            pid = len(passages)
            passages.append([d["url"], d["title"], d["kind"], d["context"], text])
            toks = tokenize(text or d["title"])
            lengths.append(len(toks))
            tf: dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            for t, n in tf.items():
                postings.setdefault(t, []).append((pid, n))

    encoded: dict[str, str] = {}
    for term in sorted(postings):
        prev, parts = 0, []
        for pid, n in postings[term]:
            parts.append(_b36(pid - prev) + (":" + _b36(n) if n > 1 else ""))
            prev = pid
        encoded[term] = ",".join(parts)
    sizes = {t: len(_dump({t: p})) - 1 for t, p in encoded.items()}
    assign = _shard_keys(sizes)
    key_size: dict[str, int] = {}
    for t, k in assign.items():
        key_size[k] = key_size.get(k, 0) + sizes[t]
    groups = _pack(sorted(key_size.items()), INDEX_TARGET, INDEX_MAX)
    key_file = {k: f"i-{n}.json" for n, g in enumerate(groups) for k in g}

    files: dict[str, bytes] = {}
    shard_terms: dict[str, dict[str, str]] = {}
    for t in sorted(encoded):
        shard_terms.setdefault(key_file[assign[t]], {})[t] = encoded[t]
    for name, terms in shard_terms.items():
        files[name] = _dump(terms)

    avg = sum(len(_dump(p)) for p in passages) / len(passages) if passages else 1
    per = max(1, round(DOC_TARGET / avg))
    for k in range(0, len(passages), per):
        files[f"d-{k // per}.json"] = _dump(passages[k:k + per])
    first: dict[str, int] = {}
    same = [[pid, first.setdefault(p[4], pid)] for pid, p in enumerate(passages)]
    files["p.json"] = _dump({"docs": table, "len": lengths, "same": [s for s in same if s[0] != s[1]]})
    files["meta.json"] = _dump({
        "v": 2,
        "kinds": sorted({d["kind"] for d in order}),
        "n": len(passages),
        "shards": key_file,
        "docshards": -(-len(passages) // per),
        "docshard_size": per,
        "stop": sorted(STOPWORDS),
    })

    os.makedirs(out_dir, exist_ok=True)
    for old in sorted(os.listdir(out_dir)):
        if re.fullmatch(r"(?:[id]-\d+|meta|p)\.json", old):
            os.remove(os.path.join(out_dir, old))
    for name in sorted(files):
        with open(os.path.join(out_dir, name), "wb") as fh:
            fh.write(files[name])
    index_sizes = [len(b) for n, b in files.items() if n.startswith("i-")]
    doc_sizes = [len(b) for n, b in files.items() if n.startswith("d-")]
    return {
        "passages": len(passages),
        "terms": len(encoded),
        "files": len(files),
        "bytes": sum(len(b) for b in files.values()),
        "largest_shard_bytes": max(index_sizes + doc_sizes, default=0),
        "largest_index_shard_bytes": max(index_sizes, default=0),
        "largest_doc_shard_bytes": max(doc_sizes, default=0),
    }
