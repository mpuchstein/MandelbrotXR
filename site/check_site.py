"""Browser checks for the built site (headless Chromium via Playwright).

Run: python3 -I site/check_site.py [--out DIR] [--no-build] [--axe-dir DIR]

Builds the site (unless --no-build), serves it with python3 -m http.server and checks:
every generated page returns HTTP 200; site pages log zero console errors, make no external
requests and contain no inline scripts; the rankings sort by every column (aria-sort, URL hash);
Blind/Reveal toggles; a search returns hits (announced in a live region); Compare opens from its URL;
every product page loads; a keyboard-only pass (theme toggle, sorting, filters, heatmap, reveal,
search, compare); skip link, landmarks and exactly one h1 on every page; every SVG chart has
role="img", <title> and <desc>; and axe-core (pinned npm package) reports zero serious or critical
violations on every page type in light and dark.
"""
import argparse
import contextlib
import functools
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
AXE_VERSION = "4.10.3"
CHROMIUM_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"]

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("check_site: Playwright is missing. Install it with:\n"
             "  python3 -m pip install --break-system-packages playwright && python3 -m playwright install --with-deps chromium")


class Fail(AssertionError):
    pass


def check(cond, msg):
    if not cond:
        raise Fail(msg)


# ---------------------------------------------------------------- setup

def axe_source(cache: str) -> str:
    """axe.min.js from the pinned npm package, installed into a cache dir on first use."""
    js = os.path.join(cache, "node_modules", "axe-core", "axe.min.js")
    if not os.path.exists(js):
        os.makedirs(cache, exist_ok=True)
        subprocess.run(["npm", "install", "--no-save", "--no-package-lock", "--no-audit", "--no-fund",
                        "--prefix", cache, f"axe-core@{AXE_VERSION}"], check=True, stdout=subprocess.DEVNULL)
    pkg = json.load(open(os.path.join(cache, "node_modules", "axe-core", "package.json")))
    check(pkg["version"] == AXE_VERSION, f"axe-core {pkg['version']} installed, expected {AXE_VERSION}")
    return open(js, encoding="utf-8").read()


@contextlib.contextmanager
def serve(root: str):
    """python3 -m http.server equivalent on a free port, in a thread."""
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(Quiet, directory=root)
    class Server(http.server.ThreadingHTTPServer):
        def handle_error(self, request, client_address):
            pass  # the browser aborting a transfer (BrokenPipe) is not a site error
    srv = Server(("127.0.0.1", 0), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/"
    finally:
        srv.shutdown()


def pages(out: str) -> tuple[list[str], list[str]]:
    """(site page URLs, product page URLs), root-relative directory-style."""
    site, play = [], []
    for d, dirs, files in os.walk(out):
        dirs.sort()
        for f in sorted(files):
            if not f.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(d, f), out).replace(os.sep, "/")
            url = rel[:-len("index.html")] if rel.endswith("index.html") else rel
            (play if rel.startswith("play/") else site).append(url)
    return site, play


def page_type(url: str) -> str:
    parts = [p for p in url.split("/") if p]
    if not parts:
        return "home"
    if parts[-1].endswith(".html") and parts[0] != "source":
        return parts[-1]
    key = parts[0]
    if key == "transcripts" and len(parts) > 1:
        return "transcripts/page" if len(parts) > 2 else "transcripts/item"
    return key + ("/item" if len(parts) > 1 and key not in ("source",) else "")


# ---------------------------------------------------------------- per-page checks

STRUCTURE_JS = """() => {
  const r = {};
  r.h1 = document.querySelectorAll('h1').length;
  const skip = document.querySelector('a.skip[href^="#"]');
  r.skip = !!skip && !!document.getElementById(skip.getAttribute('href').slice(1));
  r.landmarks = ['header', 'nav', 'main', 'footer'].filter(t => !document.querySelector(t));
  r.inline = Array.from(document.scripts).filter(s => !s.src).length;
  r.handlers = Array.from(document.querySelectorAll('*')).flatMap(e => Array.from(e.attributes).filter(a => /^on/i.test(a.name)).map(a => e.tagName + '@' + a.name)).slice(0, 5);
  r.charts = Array.from(document.querySelectorAll('svg')).filter(s => !s.closest('a, button, .qr, [aria-hidden="true"]') && s.getAttribute('aria-hidden') !== 'true' && !s.closest('figure.qr'))
    .filter(s => s.getAttribute('role') === 'img' ? !(s.querySelector(':scope > title') && s.querySelector(':scope > desc')) : s.getBoundingClientRect().width > 120)
    .map(s => (s.id || s.className.baseVal || 'svg')).slice(0, 5);
  r.overflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
  return r;
}"""


def check_structure(page, url: str, problems: list, width: int) -> None:
    r = page.evaluate(STRUCTURE_JS)
    if r["h1"] != 1:
        problems.append(f"{url}: {r['h1']} <h1> elements (need exactly 1)")
    if not r["skip"]:
        problems.append(f"{url}: no working skip link")
    if r["landmarks"]:
        problems.append(f"{url}: missing landmarks {r['landmarks']}")
    if r["inline"]:
        problems.append(f"{url}: {r['inline']} inline <script>")
    if r["handlers"]:
        problems.append(f"{url}: inline handlers {r['handlers']}")
    if r["charts"]:
        problems.append(f"{url}: SVG chart(s) without role=img + <title> + <desc>: {r['charts']}")
    if r["overflow"] > 1:
        problems.append(f"{url}: page scrolls horizontally by {r['overflow']}px at {width}px")


def run_axe(page, axe: str, url: str, problems: list, theme: str) -> int:
    page.add_script_tag(content=axe)  # evaluated by the test harness only (Playwright bypasses page CSP)
    res = page.evaluate("""async () => {
      const r = await axe.run(document, {resultTypes: ['violations']});
      return r.violations.filter(v => v.impact === 'serious' || v.impact === 'critical')
        .map(v => ({id: v.id, impact: v.impact, n: v.nodes.length, help: v.help, sample: v.nodes.slice(0, 3).map(n => n.target.join(' '))}));
    }""")
    for v in res:
        problems.append(f"axe {theme} {url}: {v['impact']} {v['id']} ×{v['n']} — {v['help']} — e.g. {v['sample']}")
    return len(res)


# ---------------------------------------------------------------- feature checks

def check_rankings(page, base: str) -> str:
    page.goto(base + "rankings/")
    table = page.locator("#rank-matrix")
    cols = page.eval_on_selector_all("#rank-matrix thead button[data-col]", "bs => bs.map(b => b.dataset.col)")
    check(len(cols) >= 5, f"rankings: only {len(cols)} sortable columns")
    def values(col):
        return page.evaluate("""(col) => {
          return Array.from(document.querySelectorAll('#rank-matrix tbody tr')).filter(r => !r.hidden)
            .map(r => { const c = r.querySelector(`:scope > [data-col="${col}"]`); return c ? (c.dataset.sort ?? c.textContent.trim()) : ''; });
        }""", col)
    def key(v):
        try:
            return (0, float(v), "")
        except ValueError:
            return (1 if v == "" else 0, 0.0, v.lower())
    for col in cols:
        btn = page.locator(f'#rank-matrix thead button[data-col="{col}"]')
        th = page.locator(f'#rank-matrix thead th:has(button[data-col="{col}"])')
        seen = set()
        for _ in range(2):
            btn.click()
            sort = th.get_attribute("aria-sort")
            check(sort in ("ascending", "descending"), f"rankings: column {col} has aria-sort={sort!r} after click")
            seen.add(sort)
            vals = [key(v) for v in values(col)]
            filled = [v for v in vals if not (v[0] == 1 and v[2] == "")]
            exp = sorted(filled, reverse=(sort == "descending"))
            check(filled == exp, f"rankings: column {col} not sorted {sort}: {[v[1] if v[2] == '' else v[2] for v in filled]}")
            h = urllib.parse.unquote(page.evaluate("location.hash"))
            check(f"sort={col}-" in h or (h in ("", "#") and col == cols[0] and sort == "ascending"),
                  f"rankings: hash lacks sort state for {col} {sort} ({h!r}); only the default order may omit it")
        check(seen == {"ascending", "descending"}, f"rankings: column {col} did not toggle both directions")
    # hash state restores on load
    page.goto(base + f"rankings/#sort={cols[-1]}-desc")
    page.wait_for_timeout(100)
    check(page.locator(f'#rank-matrix thead th:has(button[data-col="{cols[-1]}"])').get_attribute("aria-sort") == "descending",
          "rankings: sort state not restored from the URL hash")
    return f"{len(cols)} columns sorted both ways"


def check_reveal(page, base: str, judge_url: str, review_url: str) -> str:
    for url in (judge_url, review_url):
        page.goto(base + url)
        btn = page.locator("[data-reveal-toggle]").first
        check(btn.get_attribute("aria-pressed") == "false", f"{url}: reveal toggle not initially blind")
        blind = page.locator("[data-reveal-scope]").first.inner_text()
        btn.click()
        check(btn.get_attribute("aria-pressed") == "true", f"{url}: reveal toggle did not press")
        shown = page.locator("[data-reveal-scope]").first.inner_text()
        check(shown != blind, f"{url}: revealing changed nothing visible")
        btn.click()
        check(btn.get_attribute("aria-pressed") == "false", f"{url}: reveal toggle did not release")
    return "judge and review pages toggle"


def check_search(page, base: str) -> str:
    page.goto(base + "search/?q=perturbation")
    page.wait_for_function("document.querySelectorAll('#search-results li').length > 0", timeout=15000)
    n = page.locator("#search-results li").count()
    status = page.locator("#search-status")
    check(status.get_attribute("aria-live") == "polite" and status.inner_text().strip(), "search: no polite live status")
    check(page.locator("#search-results mark").count() > 0, "search: no highlighted matches")
    return f"{n} hits for 'perturbation'"


def check_compare(page, base: str, a: str, b: str) -> str:
    resp = page.goto(base + f"compare/{a}-vs-{b}/")
    check(resp and resp.status == 200, f"compare/{a}-vs-{b}/ did not load")
    body = page.locator("main").inner_text()
    page.goto(base + f"compare/?a={b}&b={a}")
    page.wait_for_url(re.compile(rf"compare/{re.escape(b)}-vs-{re.escape(a)}/"), timeout=5000)
    return f"pair page and ?a=&b= redirect ({len(body)} chars)"


def check_keyboard(page, base: str, a: str, b: str, judge_url: str) -> str:
    """Operate every interactive feature with the keyboard only."""
    done = []
    def tab_to(selector, limit=400):
        page.keyboard.press("Tab")
        for _ in range(limit):
            if page.evaluate("(s) => document.activeElement && document.activeElement.matches(s)", selector):
                vis = page.evaluate("""() => { const s = getComputedStyle(document.activeElement);
                    return (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== 'none'; }""")
                check(vis, f"keyboard: no visible focus indicator on {selector}")
                return
            page.keyboard.press("Tab")
        raise Fail(f"keyboard: could not reach {selector} with Tab")

    page.goto(base)
    tab_to("a.skip")
    tab_to("#theme-toggle")
    before = page.get_attribute("#theme-toggle", "aria-pressed")
    page.keyboard.press("Enter")
    check(page.get_attribute("#theme-toggle", "aria-pressed") != before, "keyboard: theme toggle did not change")
    page.keyboard.press("Space")
    check(page.get_attribute("#theme-toggle", "aria-pressed") == before, "keyboard: theme toggle did not change back")
    done.append("theme")

    page.goto(base + "rankings/")
    col = page.eval_on_selector("#rank-matrix thead button[data-col]", "b => b.dataset.col")
    tab_to(f'#rank-matrix thead button[data-col="{col}"]')
    page.keyboard.press("Enter")
    check(page.locator(f'#rank-matrix thead th:has(button[data-col="{col}"])').get_attribute("aria-sort") in ("ascending", "descending"),
          "keyboard: sorting by Enter failed")
    check(page.locator("#rank-status").inner_text().strip() != "", "keyboard: sort change not announced")
    done.append("sort")
    tab_to("#rank-heat")
    page.keyboard.press("Space")
    check(page.get_attribute("#rank-heat", "aria-pressed") == "true", "keyboard: heatmap toggle failed")
    done.append("heatmap")
    sel = page.locator("#rank-controls select, #rank-controls input").first
    tag = sel.evaluate("e => e.tagName.toLowerCase() + (e.type ? ':' + e.type : '')")
    sel.focus()
    if tag.startswith("select"):
        page.keyboard.press("ArrowDown")
    else:
        page.keyboard.press("Space")
    page.wait_for_timeout(50)
    check("=" in urllib.parse.unquote(page.evaluate("location.hash")), "keyboard: filter did not change the view state")
    done.append("filters")

    page.goto(base + judge_url)
    tab_to("[data-reveal-toggle]")
    page.keyboard.press("Enter")
    check(page.locator("[data-reveal-toggle]").first.get_attribute("aria-pressed") == "true", "keyboard: reveal failed")
    done.append("reveal")

    page.goto(base + "search/")
    tab_to("#q")
    page.keyboard.type("gaze")
    page.wait_for_function("document.querySelectorAll('#search-results li').length > 0", timeout=15000)
    done.append("search")

    page.goto(base + "compare/")
    tab_to("select")
    page.keyboard.press("ArrowDown")
    page.wait_for_timeout(300)
    done.append("compare")
    return ", ".join(done)


# ---------------------------------------------------------------- screenshots

def screenshot_targets(model) -> list[tuple[str, str]]:
    """(name, root-relative URL) — one representative page per page type."""
    order = model.ordered()
    c0, c1 = order[0], order[-1]
    j = model.judges[0]
    r = model.reviews[0]
    from sitelib.layout import transcript_id
    return [
        ("home", ""), ("rankings", "rankings/"), ("candidates", "candidates/"), ("candidate", f"candidates/{c0.slug}/"),
        ("compare", "compare/"), ("compare-pair", f"compare/{c0.slug}-vs-{c1.slug}/"), ("techniques", "techniques/"),
        ("judges", "judges/"), ("judge", f"judges/{j.id.replace('_', '-')}/"), ("reviews", "reviews/"),
        ("review", f"reviews/{r.type_id.replace('_', '-')}/{r.slug}/"), ("transcripts", "transcripts/"),
        ("transcript", f"transcripts/{transcript_id(c0.transcription)}/"), ("source", "source/Judge/README.md.html"),
        ("methodology", "methodology/"), ("data", "data/"), ("changelog", "data/changelog/"),
        ("search", "search/?q=perturbation"),
    ]


def take_screenshots(browser, base: str, model, dest: str, max_height: int) -> int:
    """PNG per page type at 390×844 and 1440×900 in light and dark, capped at max_height px."""
    os.makedirs(dest, exist_ok=True)
    n = 0
    for theme in ("light", "dark"):
        for w, h in ((390, 844), (1440, 900)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=theme, reduced_motion="reduce")
            page = ctx.new_page()
            for name, url in screenshot_targets(model):
                page.goto(base + url, wait_until="load")
                if name == "search":
                    page.wait_for_function("document.querySelectorAll('#search-results li').length > 0", timeout=15000)
                page.evaluate("() => Promise.all(Array.from(document.images).map(i => (i.loading = 'eager', i.decode().catch(() => null))))")
                height = min(max_height, page.evaluate("document.documentElement.scrollHeight"))
                page.set_viewport_size({"width": w, "height": height})
                page.screenshot(path=os.path.join(dest, f"{name}-{w}-{theme}.png"))
                page.set_viewport_size({"width": w, "height": h})
                n += 1
            ctx.close()
    return n


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=os.path.join(HERE, "dist"))
    ap.add_argument("--no-build", action="store_true", help="check an existing build")
    ap.add_argument("--axe-dir", default=os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "mandelbrotxr-axe"))
    ap.add_argument("--axe-all", action="store_true", help="run axe on every page, not one per page type")
    ap.add_argument("--screenshots", metavar="DIR", help="only write page-type screenshots (390/1440, light/dark) to DIR")
    ap.add_argument("--max-height", type=int, default=2400, help="screenshot height cap in px (default 2400)")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    if not a.no_build:
        subprocess.run([sys.executable, "-I", os.path.join(HERE, "build.py"), "--out", out], check=True)
    axe = None if a.screenshots else axe_source(a.axe_dir)
    site_pages, play_pages = pages(out)
    sys.path.insert(0, HERE)
    from sitelib import data
    model = data.load(REPO)
    order = model.ordered()
    ca, cb = order[0].slug, order[1].slug
    judge_url = f"judges/{model.judges[0].id.replace('_', '-')}/"
    review_url = f"reviews/{model.reviews[0].type_id.replace('_', '-')}/{model.reviews[0].slug}/"

    problems, results = [], {}
    if a.screenshots:
        with serve(out) as base, sync_playwright() as p:
            browser = p.chromium.launch(args=CHROMIUM_ARGS)
            n = take_screenshots(browser, base, model, os.path.abspath(a.screenshots), a.max_height)
            browser.close()
        print(f"wrote {n} screenshots to {a.screenshots}")
        return 0
    with serve(out) as base, sync_playwright() as p:
        browser = p.chromium.launch(args=CHROMIUM_ARGS)
        host = urllib.parse.urlsplit(base).netloc

        def context(**kw):
            ctx = browser.new_context(**kw)
            ctx.set_default_timeout(15000)
            return ctx

        # 1. every page: HTTP 200, console, external requests, structure
        ctx = context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        errors, external = [], []
        page.on("console", lambda m: m.type == "error" and errors.append((page.url, m.text)))
        page.on("pageerror", lambda e: errors.append((page.url, str(e))))
        page.on("request", lambda r: urllib.parse.urlsplit(r.url).netloc not in (host, "") and not r.url.startswith("data:") and external.append((page.url, r.url)))
        for url in site_pages:
            resp = page.goto(base + url, wait_until="load")
            if not resp or resp.status != 200:
                problems.append(f"{url}: HTTP {resp.status if resp else 'no response'}")
                continue
            if url.endswith(".html") or url.endswith("/") or url == "":
                check_structure(page, url, problems, 390)
        results["pages"] = f"{len(site_pages)} site pages: HTTP 200 checked"
        for u, e in errors:
            problems.append(f"console error on {u}: {e}")
        for u, r in external:
            problems.append(f"external request from {u}: {r}")
        results["console"] = f"{len(errors)} console errors"
        results["external"] = f"{len(external)} external requests"
        ctx.close()

        # 2. products load (byte-identical copies; their own console output is not checked)
        ctx = context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        page.on("dialog", lambda d: d.dismiss())
        for url in play_pages:
            resp = page.goto(base + url, wait_until="domcontentloaded")
            if not resp or resp.status != 200:
                problems.append(f"{url}: HTTP {resp.status if resp else 'no response'}")
            else:
                page.wait_for_timeout(500)
                check(page.title() is not None, f"{url}: no document")
        results["products"] = f"{len(play_pages)} product pages loaded"
        ctx.close()

        # 3. features + keyboard (desktop), with console capture
        for theme in ("light",):
            ctx = context(viewport={"width": 1440, "height": 900}, color_scheme=theme)
            page = ctx.new_page()
            ferr = []
            page.on("console", lambda m: m.type == "error" and ferr.append((page.url, m.text)))
            page.on("pageerror", lambda e: ferr.append((page.url, str(e))))
            for name, fn in (("rankings sort", lambda: check_rankings(page, base)),
                             ("blind/reveal", lambda: check_reveal(page, base, judge_url, review_url)),
                             ("search", lambda: check_search(page, base)),
                             ("compare", lambda: check_compare(page, base, ca, cb)),
                             ("keyboard", lambda: check_keyboard(page, base, ca, cb, judge_url))):
                try:
                    results[name] = fn()
                except Fail as e:
                    problems.append(str(e))
                except Exception as e:  # playwright timeouts etc.
                    problems.append(f"{name}: {type(e).__name__}: {str(e).splitlines()[0]}")
            problems += [f"console error during feature checks on {u}: {t}" for u, t in ferr]
            ctx.close()

        # 4. axe-core on every page type (or every page) in light and dark
        by_type = {}
        for url in site_pages:
            if url.endswith((".xml", ".json", ".csv")):
                continue
            by_type.setdefault(page_type(url), url)
        targets = [u for u in site_pages if not u.endswith((".xml", ".json", ".csv"))] if a.axe_all else sorted(by_type.values())
        nviol = 0
        for theme in ("light", "dark"):
            for width in (390, 1440):
                ctx = context(viewport={"width": width, "height": 900}, color_scheme=theme)
                page = ctx.new_page()
                for url in targets:
                    page.goto(base + url, wait_until="load")
                    nviol += run_axe(page, axe, url, problems, f"{theme}/{width}")
                ctx.close()
        results["axe"] = f"{len(targets)} page types × light/dark × 390/1440: {nviol} serious/critical violations"
        browser.close()

    for k, v in results.items():
        print(f"  {k}: {v}")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for pr in problems[:200]:
            print("  -", pr)
        return 1
    print("all site checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
