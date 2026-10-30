"""Search: search/ (the page) and search-index/ (the index files).

Runs last (ORDER 1000) so every other page module has registered its documents with site.search_doc().
The index is built by sitelib/searchindex.py and queried in the browser by assets/js/search.js; this
module writes the page with search.js's client contract:
  <form id="search-form" data-index="…/search-index/" data-root="…/"> with <input id="q" name="q">,
  #search-kinds (kind filters, filled by the script), #search-status (aria-live) and #search-results.
Without JavaScript the form still submits (GET ?q=…) and the page explains where to browse instead.
"""
from __future__ import annotations

import os
import sys
from urllib.parse import quote

from .. import searchindex
from ..data import DataError
from ..layout import Site, esc

ORDER = 1000

EXAMPLES = ["perturbation", "alert", '"Cardboard stereo"', "hallucination", "gaze dwell", "shader compile"]


def build(site: Site) -> None:
    docs = site.search_docs
    if not docs:
        raise DataError("site/sitelib/pages/search.py: no search documents were registered; the search index would be empty")
    stats = searchindex.build(docs, os.path.join(site.out, "search-index"))
    if not stats.get("passages"):
        raise DataError("site/sitelib/pages/search.py: the search index has no passages")
    kinds: dict[str, int] = {}
    for d in docs:
        kinds[d["kind"]] = kinds.get(d["kind"], 0) + 1
    print(f"search: {len(docs)} documents, {stats['passages']} passages, {stats['terms']} terms, "
          f"{stats['files']} files, {stats['bytes']:,} bytes (largest shard {stats['largest_shard_bytes']:,} B)", file=sys.stderr)

    ex = " ".join(f'<a class="chip" href="@/search/?q={quote(q)}">{esc(q)}</a>' for q in EXAMPLES)
    kind_list = ", ".join(f"{esc(k)} ({n})" for k, n in sorted(kinds.items()))
    body = f"""<header class="search-head"><h1>Search</h1>
<p class="lede">Full-text search over the reviews, judge rankings and summaries, the techniques catalog, the methodology and every transcript.</p></header>
<form id="search-form" role="search" method="get" action="@/search/" data-index="@/search-index/" data-root="@/">
<label for="q" class="sr-only">Search the results</label>
<input type="search" id="q" name="q" autocomplete="off" spellcheck="false" placeholder="Search reviews, rankings, transcripts…" aria-describedby="search-help">
<button type="submit" class="btn btn-primary">Search</button>
<div id="search-kinds" role="group" aria-label="Filter by kind"></div>
</form>
<p id="search-help" class="small muted">All words must match; the last word also matches as a prefix while you type; put a phrase in "quotes" to match it exactly.</p>
<p class="search-examples small"><span class="muted">Try:</span> {ex}</p>
<p id="search-status" aria-live="polite"></p>
<ol id="search-results"></ol>
<p class="nojs-note small muted">Search runs in your browser and needs JavaScript. Without it, browse the
<a href="@/rankings/">Rankings</a>, <a href="@/candidates/">Candidates</a>, <a href="@/judges/">Judges &amp; reviews</a>,
<a href="@/techniques/">Techniques</a> and <a href="@/transcripts/">Transcripts</a> indexes.
The index covers {len(docs):,} documents in {stats['passages']:,} passages: {kind_list}.</p>"""
    site.page("search/index.html", "Search", body, section="search", crumbs=[("Search", "")], scripts=["search.js"],
              description="Search the MandelbrotXR reviews, judge rankings, summaries and transcripts.")
    index_page(site, stats, len(docs))


def index_page(site: Site, stats: dict, n_docs: int) -> None:
    """search-index/index.html: what the index files are (the directory is also search.js's data-index)."""
    d = os.path.join(site.out, "search-index")
    names = sorted((n for n in os.listdir(d) if n.endswith(".json")), key=lambda n: (n[0] not in "mp", len(n), n))
    rows = "".join(f'<tr><th scope="row"><a href="@/search-index/{esc(n)}"><code>{esc(n)}</code></a></th>'
                   f'<td class="num">{os.path.getsize(os.path.join(d, n)):,} B</td></tr>' for n in names)
    body = f"""<header><h1>Search index</h1>
<p class="lede">The files behind <a href="@/search/">Search</a>, built with the site: {n_docs:,} documents split into
{stats['passages']:,} passages and {stats['terms']:,} terms. The page loads <code>meta.json</code> and <code>p.json</code>,
then only the shards a query needs.</p></header>
<p>The format is documented at the top of <code>site/sitelib/searchindex.py</code>: <code>meta.json</code> (shard map and stop words),
<code>p.json</code> (document table and passage lengths), <code>i-*.json</code> (postings by term prefix) and <code>d-*.json</code> (passage text).</p>
<div class="table-wrap"><table><caption class="sr-only">Search index files and sizes</caption>
<thead><tr><th scope="col">File</th><th scope="col" class="num">Size</th></tr></thead><tbody>{rows}</tbody></table></div>"""
    site.page("search-index/index.html", "Search index", body, section="search",
              crumbs=[("Search", "search/"), ("Search index", "")],
              description="The static full-text search index of the MandelbrotXR results site.")
