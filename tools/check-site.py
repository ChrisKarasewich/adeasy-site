# check-site.py: pre-upload checks. Run from the repo root; fix anything it reports before uploading.
#
#   python3 tools/check-site.py
#
# Checks: every local link and image resolves, no orphan files, no placeholders, every page has the
# same head essentials (title, description, canonical, OG, favicon, CSS set, valid JSON-LD), canonicals
# match the sitemap, phone numbers and emails are AdEasy's, and no em dashes in page copy.

import json
import os
import re
import sys
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import site_config as C  # noqa: E402

ALLOWED_ORPHANS = {"robots.txt", "sitemap.xml", "llms.txt", "404.html", "_redirects", "_headers", "wrangler.jsonc",
                   ".assetsignore", "site.webmanifest", "favicon.ico", "favicon.svg", "apple-touch-icon.png",
                   "icon-192.png", "icon-512.png", "README.md", "CHANGELOG.md", ".prettierrc", ".gitignore",
                   "blocks.css"}  # blocks.css is inlined into every page head by build-html.py
SKIP_DIRS = {"tools", "_source", ".git"}
PLACEHOLDERS = re.compile(r"GTM-X{4,}|555-|example\.com|lorem|TODO|XXXX|Placeholder ·", re.I)
GOOD_TEL = {"tel:+12048094978"}
GOOD_MAIL = {"mailto:support@adeasy.com", "mailto:careers@adeasy.com", "mailto:chris@adeasy.com"}

problems = []


def bad(page, msg):
    problems.append(f"{page}: {msg}")


def site_files():
    out = set()
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not (d == ROOT and x.startswith("."))]
        for f in files:
            out.add(os.path.relpath(os.path.join(d, f), ROOT))
    return out


def resolve(path):
    """Map a site URL path to the file Cloudflare would serve, or None."""
    p = unquote(path).lstrip("/")
    for cand in (p, p + ".html", os.path.join(p, "index.html"), p.rstrip("/") + ".html"):
        if cand and os.path.isfile(os.path.join(ROOT, cand)):
            return os.path.normpath(cand)
    if p == "":
        return "index.html"
    return None


def main():
    files = site_files()
    html_files = sorted(f for f in files if f.endswith(".html"))
    referenced = set()
    sitemap = set(re.findall(r"<loc>([^<]+)</loc>", open(os.path.join(ROOT, "sitemap.xml")).read()))
    css_sets = {}
    for f in html_files:
        raw = open(os.path.join(ROOT, f)).read()
        soup = BeautifulSoup(raw, "html.parser")
        # head essentials
        if not soup.title or not soup.title.string:
            bad(f, "no <title>")
        for sel, what in (('meta[name="description"]', "description"), ('meta[property="og:image"]', "og:image"),
                          ('meta[property="og:title"]', "og:title"), ('link[rel="icon"]', "favicon"),
                          ('meta[name="twitter:card"]', "twitter:card")):
            if not soup.select_one(sel):
                bad(f, f"missing {what}")
        if soup.html.get("lang") != "en-CA":
            bad(f, "lang is not en-CA")
        canon = soup.select_one('link[rel="canonical"]')
        noindex = "noindex" in (soup.select_one('meta[name="robots"]') or {}).get("content", "")
        if canon and not noindex and canon["href"] not in sitemap:
            bad(f, f"canonical {canon['href']} not in sitemap")
        if not canon and f != "404.html":
            bad(f, "missing canonical")
        for s in soup.select('script[type="application/ld+json"]'):
            try:
                json.loads(s.string)
            except Exception as e:  # noqa: BLE001
                bad(f, f"invalid JSON-LD: {e}")
        if len(soup.find_all("main")) != 1 or not soup.find("main", id="main"):
            bad(f, "needs exactly one <main id=main>")
        css_sets[f] = tuple(sorted(l["href"] for l in soup.select('link[rel="stylesheet"]') if l["href"].startswith("/")))
        if C.GTM_ID and C.GTM_ID not in raw and f != "404.html":
            bad(f, "GTM container missing")
        # copy checks
        text = soup.body.get_text(" ")
        if PLACEHOLDERS.search(raw):
            bad(f, "placeholder text: " + PLACEHOLDERS.search(raw).group(0))
        if "—" in text:
            bad(f, "em dash in copy: …" + text[max(0, text.find("—") - 40): text.find("—") + 20].strip() + "…")
        for a in soup.select('a[href^="tel:"]'):
            if a["href"] not in GOOD_TEL:
                bad(f, "unexpected phone link " + a["href"])
        for a in soup.select('a[href^="mailto:"]'):
            if a["href"].split("?")[0] not in GOOD_MAIL:
                bad(f, "unexpected email link " + a["href"])
        # local references
        refs = []
        for t in soup.find_all(True):
            for attr in ("href", "src", "action", "data-full"):
                if t.get(attr):
                    refs.append(t[attr])
            for attr in ("srcset", "imagesrcset"):
                if t.get(attr):
                    refs += [x.strip().split(" ")[0] for x in t[attr].split(",")]
        for r in refs:
            u = urlparse(r)
            if u.scheme or u.netloc or r.startswith(("#", "tel:", "mailto:", "data:")):
                continue
            if not r.startswith("/"):
                bad(f, f"relative link {r}")
                continue
            hit = resolve(u.path)
            if not hit:
                bad(f, f"broken link {r}")
            else:
                referenced.add(hit)
    # every page loads the same CSS set
    common = max(set(css_sets.values()), key=list(css_sets.values()).count)
    for f, s in css_sets.items():
        if s != common:
            bad(f, f"different stylesheet set {s}")
    # CSS url() references
    for f in files:
        if f.endswith(".css"):
            for r in re.findall(r"url\(['\"]?(/[^'\")]+)", open(os.path.join(ROOT, f)).read()):
                hit = resolve(r)
                if hit:
                    referenced.add(hit)
                else:
                    bad(f, f"broken url({r})")
    # manifest icons, og images and pages count as referenced
    referenced |= {"icon-192.png", "icon-512.png"} | set(html_files)
    for f in html_files:
        for m in re.findall(r'content="https://adeasy\.com(/assets/[^"]+)"', open(os.path.join(ROOT, f)).read()):
            if resolve(m):
                referenced.add(resolve(m))
            else:
                bad(f, f"og image missing {m}")
    for f in sorted(files - referenced):
        if os.path.basename(f) not in ALLOWED_ORPHANS and f not in ALLOWED_ORPHANS:
            bad(f, "file is not used by any page")
    print(f"{len(html_files)} pages, {len(files)} files checked")
    if problems:
        print("\n".join(problems))
        print(f"\n{len(problems)} problem(s)")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
