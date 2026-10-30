"""Build the MandelbrotXR results site (static HTML/CSS/JS) from the committed repo data.

Usage: python3 -I site/build.py [--out DIR] [--base-url URL] [--pages a,b,...]

Stdlib only. Output is deterministic: the same commit gives byte-identical files.
See site/README.md for the data model and how to extend the site.
"""
import argparse
import hashlib
import importlib
import os
import pkgutil
import shutil
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I does not put the script's directory on sys.path

from sitelib import data, fragments, layout  # noqa: E402
from sitelib.data import DataError  # noqa: E402

MARKER = ".mandelbrotxr-site"


def prepare_out(out: str) -> None:
    """Empty the output directory, refusing to wipe anything that is not a previous build."""
    if os.path.exists(out):
        if not os.path.isdir(out):
            sys.exit(f"build: --out {out} exists and is not a directory")
        if os.listdir(out) and not os.path.exists(os.path.join(out, MARKER)):
            sys.exit(f"build: refusing to clear {out}: it is not empty and has no {MARKER} marker")
        shutil.rmtree(out)
    os.makedirs(out)
    with open(os.path.join(out, MARKER), "w") as f:
        f.write("MandelbrotXR site build output; safe to delete.\n")


def build_assets(site: layout.Site) -> None:
    """assets/site.css = base.css + every other css (sorted); js/, vendor/ and root files copied.
    Each asset gets a content-hash query suffix for cache busting."""
    src, dst = os.path.join(HERE, "assets"), os.path.join(site.out, "assets")
    os.makedirs(dst, exist_ok=True)
    css_dir = os.path.join(src, "css")
    names = sorted(n for n in os.listdir(css_dir) if n.endswith(".css"))
    names.sort(key=lambda n: n != "base.css")
    css = "".join(f"/* {n} */\n" + open(os.path.join(css_dir, n), encoding="utf-8").read().rstrip() + "\n\n" for n in names)
    files = {"site.css": css.encode()}
    for sub in ("js", "vendor"):
        root = os.path.join(src, sub)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            for n in sorted(filenames):
                p = os.path.join(dirpath, n)
                files[os.path.relpath(p, src).replace(os.sep, "/")] = open(p, "rb").read()
    for n in sorted(os.listdir(src)):
        if os.path.isfile(os.path.join(src, n)):
            files[n] = open(os.path.join(src, n), "rb").read()
    for name, content in sorted(files.items()):
        site.write(f"assets/{name}", content)
        site.assets[name] = "?v=" + hashlib.sha256(content).hexdigest()[:10]


def copy_products(site: layout.Site) -> None:
    """play/<slug>/index.html: byte-for-byte product copies, re-verified against source-html.sha256."""
    for c in site.model.candidates:
        rel = f"play/{c.slug}/index.html"
        os.makedirs(os.path.join(site.out, "play", c.slug), exist_ok=True)
        shutil.copyfile(os.path.join(site.repo, c.html_path), os.path.join(site.out, rel))
        got = hashlib.sha256(open(os.path.join(site.out, rel), "rb").read()).hexdigest()
        if got != c.sha256:
            raise DataError(f"{site.model.sha_file}: copied {rel} has sha256 {got}, expected {c.sha256}")


def page_modules(only: set[str] | None):
    import sitelib.pages as pkg
    mods = []
    for info in pkgutil.iter_modules(pkg.__path__):
        if info.name.startswith("_") or (only and info.name not in only):
            continue
        mods.append(importlib.import_module(f"sitelib.pages.{info.name}"))
    return sorted(mods, key=lambda m: (getattr(m, "ORDER", 500), m.__name__))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=os.path.join(HERE, "dist"), help="output directory (default: site/dist/)")
    ap.add_argument("--base-url", default="https://mandelbrotxr.puchstein.dev/",
                    help="absolute site URL, used only for QR codes, the Atom feed and canonical links")
    ap.add_argument("--repo", default=os.path.dirname(HERE), help=argparse.SUPPRESS)
    ap.add_argument("--pages", default="", help="comma-separated page modules to build (development only)")
    a = ap.parse_args(argv)
    base = a.base_url if a.base_url.endswith("/") else a.base_url + "/"
    try:
        gitinfo = data.git_info(a.repo)
        model = data.load(a.repo)
        fragments.bind(model)
        out = os.path.abspath(a.out)
        prepare_out(out)
        site = layout.Site(model, out, base, gitinfo)
        build_assets(site)
        copy_products(site)
        for mod in page_modules(set(filter(None, a.pages.split(","))) or None):
            mod.build(site)
    except DataError as e:
        print(f"build: data error: {e}", file=sys.stderr)
        return 2
    print(f"build: {len(site.pages)} pages, {len(model.candidates)} candidates, {len(model.judges)} judges, "
          f"{len(model.reviews)} reviews -> {out} ({gitinfo['version'][:12]}, {gitinfo['date']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
