# build-html.py: assembles every page from _source/ into the site root.
#
#   python3 tools/build-html.py            production build (absolute, extensionless URLs)
#   python3 tools/build-html.py --demo DIR  review copy for a Claude artifact: relative .html links,
#                                          fallback images only, noindex, no tracking
#
# Each page = shared head + header partial + _source/pages/<name>.html + footer partials.
# IDs and keys come from tools/site_config.py. Page list and URLs come from tools/pages.py.
# Images: <img src="/assets/img/x.jpg"> in a page source becomes a <picture> with AVIF and WebP
# sources from _source/image-manifest.json (written by build-images.py).

import html
import json
import os
import posixpath
import re
import shutil
import sys
from datetime import date

from bs4 import BeautifulSoup, Comment

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import site_config as C  # noqa: E402
from pages import NOINDEX, PAGES, out_file  # noqa: E402

SRC = os.path.join(ROOT, "_source")
def ASSET_V(rel):
    """Short content hash for a CSS/JS file, so browsers fetch the new copy whenever it changes
    (assets are cached for 30 days)."""
    import hashlib
    return hashlib.md5(open(os.path.join(ROOT, "assets", rel), "rb").read()).hexdigest()[:8]


META = json.load(open(os.path.join(SRC, "pages", "meta.json")))
MANIFEST = json.load(open(os.path.join(SRC, "image-manifest.json")))
SEO = json.load(open(os.path.join(SRC, "seo.json")))  # approved titles, descriptions, OG images, dates
PARTIAL = lambda n: open(os.path.join(SRC, "partials", n)).read()
URL_TO_NAME = {u: n for (u, n, *_r) in PAGES}
BY_URL = {u: dict(zip(("url", "name", "nav", "type", "parent"), row)) for row in PAGES for u in [row[0]]}
TODAY = date.today().isoformat()

FONTS = "https://fonts.googleapis.com/css2?family=Alfa+Slab+One&family=Chivo:ital,wght@0,400;0,700;1,400&family=IBM+Plex+Mono:wght@400;700&display=swap"


def esc(s):
    return html.escape(s or "", quote=True)


def abs_url(path):
    return C.SITE + path


# ---------- Images ----------

def picture(img, eager=False):
    """Wrap a site image in <picture> with AVIF/WebP sources; add size, decoding and loading hints."""
    src = img.get("src", "")
    if not src.startswith("/assets/img/"):
        return
    key = src[len("/assets/img/"):]
    m = MANIFEST.get(key)
    if not m:
        raise SystemExit(f"Image not in manifest: {src}")
    if m.get("svg"):
        return
    img["src"] = "/assets/img/" + m["fallback"]
    # width/height attributes: the size the image is shown at on desktop (its CSS usually overrides
    # this); they give the browser the aspect ratio so nothing shifts while the image loads.
    shown = m["d"] or m["m"] or m["w"]
    img["width"], img["height"] = str(shown), str(round(shown * m["h"] / m["w"]))
    img["decoding"] = "async"
    if eager:
        img["fetchpriority"] = "high"
        if "loading" in img.attrs:
            del img["loading"]
    else:
        img["loading"] = "lazy"
    if img.find_parent("button", class_="gal-thumb"):
        img["data-full"] = "/assets/img/" + m["fallback"]
    vs = m["variants"]
    sizes = f"(max-width: 680px) {m['m'] or 92}px, {m['d'] or m['w']}px" if (m["m"] or m["d"]) else "100vw"
    if m["m"] and not m["d"]:
        sizes = f"{m['m']}px"
    if len(vs) > 1:
        img["srcset"] = ", ".join(f"/assets/img/{v['fallback']} {v['w']}w" for v in vs)
        img["sizes"] = sizes
    parent = img.parent
    if parent is not None and parent.name == "picture":
        # Art-directed picture (a different crop on phones): expand each <source media> too.
        for old in parent.find_all("source"):
            key2 = old["srcset"].split()[0][len("/assets/img/"):]
            m2 = MANIFEST[key2]
            media = old.get("media")
            for kind in ("avif", "webp"):
                s = BeautifulSoup("", "html.parser").new_tag("source", type=f"image/{kind}", media=media)
                s["srcset"] = ", ".join(f"/assets/img/{v[kind]} {v['w']}w" for v in m2["variants"])
                s["sizes"] = f"{m2['m'] or 92}px"
                old.insert_before(s)
            old["srcset"] = ", ".join(f"/assets/img/{v['fallback']} {v['w']}w" for v in m2["variants"])
            old["sizes"] = f"{m2['m'] or 92}px"
            m["mobile"] = m2
        for kind in ("avif", "webp"):
            s = BeautifulSoup("", "html.parser").new_tag("source", type=f"image/{kind}")
            s["srcset"] = ", ".join(f"/assets/img/{v[kind]} {v['w']}w" for v in vs)
            if len(vs) > 1:
                s["sizes"] = sizes
            img.insert_before(s)
        return m
    pic = BeautifulSoup("", "html.parser").new_tag("picture", style="display:contents")
    for kind in ("avif", "webp"):
        s = BeautifulSoup("", "html.parser").new_tag("source", type=f"image/{kind}")
        s["srcset"] = ", ".join(f"/assets/img/{v[kind]} {v['w']}w" for v in vs)
        if len(vs) > 1:
            s["sizes"] = sizes
        pic.append(s)
    img.wrap(pic)
    # move sources before the img
    for s in pic.find_all("source"):
        img.insert_before(s.extract())
    return m


# ---------- Head ----------

def schema_for(p, page_soup):
    out = []
    org = {
        "@type": "ProfessionalService",
        "@id": C.SITE + "/#organization",
        "name": C.ORG["name"],
        "legalName": C.ORG["legalName"],
        "url": C.SITE + "/",
        "logo": C.SITE + "/icon-512.png",
        "image": C.SITE + "/assets/img/og/home-og.jpg",
        "telephone": C.ORG["phone"],
        "email": C.ORG["email"],
        "address": {"@type": "PostalAddress", "streetAddress": C.ORG["street"], "addressLocality": C.ORG["city"],
                    "addressRegion": C.ORG["region"], "postalCode": C.ORG["postal"], "addressCountry": C.ORG["country"]},
        "foundingDate": C.ORG["foundingDate"],
        "founder": {"@type": "Person", "@id": C.SITE + "/about#chris-karasewich", "name": C.ORG["founder"],
                    "jobTitle": "Founder and President", "sameAs": [C.ORG["founder_linkedin"]]},
        "areaServed": [{"@type": "Country", "name": "Canada"}],
        "description": SEO["/"]["description"],
        "sameAs": C.ORG["sameAs"],
    }
    if p["url"] == "/":
        out.append(org)
        out.append({"@type": "WebSite", "@id": C.SITE + "/#website", "name": "AdEasy", "url": C.SITE + "/",
                    "publisher": {"@id": C.SITE + "/#organization"}})
    else:
        crumbs, u = [], p["url"]
        while u:
            name = SEO[u]["crumb"]
            crumbs.insert(0, (name, u))
            u = BY_URL[u]["parent"]
        out.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": abs_url(x)} for i, (n, x) in enumerate(crumbs)]})
    if p["type"] in ("service", "service-hub"):
        out.append({"@type": "Service", "name": SEO[p["url"]]["crumb"], "serviceType": "Marketing for home-service businesses",
                    "provider": {"@id": C.SITE + "/#organization"}, "areaServed": {"@type": "Country", "name": "Canada"},
                    "url": abs_url(p["url"]), "description": SEO[p["url"]]["description"]})
    if p["type"] == "post" and SEO[p["url"]].get("datePublished"):
        s = SEO[p["url"]]
        out.append({"@type": "Article", "headline": s["h1"], "description": s["description"],
                    "image": C.SITE + s["og"], "datePublished": s["datePublished"],
                    "author": {"@type": "Person", "@id": C.SITE + "/about#chris-karasewich", "name": C.ORG["founder"],
                               "url": C.SITE + "/about"},
                    "publisher": {"@id": C.SITE + "/#organization"}, "mainEntityOfPage": abs_url(p["url"])})
    if p["type"] == "about":
        out.append({"@type": "AboutPage", "url": abs_url(p["url"]), "about": {"@id": C.SITE + "/#organization"}})
    # FAQPage from <details><summary> blocks on the page
    faqs = []
    for d in page_soup.find_all("details"):
        q = d.find("summary")
        if not q:
            continue
        qt = q.get_text(" ", strip=True).rstrip("+−- ").strip()
        q.extract()
        at = d.get_text(" ", strip=True)
        d.insert(0, q)
        if qt and at:
            faqs.append({"@type": "Question", "name": qt, "acceptedAnswer": {"@type": "Answer", "text": at}})
    if faqs:
        out.append({"@type": "FAQPage", "mainEntity": faqs})
    return {"@context": "https://schema.org", "@graph": out}


def head(p, schema, demo, hero):
    s = SEO[p["url"]]
    url = abs_url(p["url"])
    og = C.SITE + s["og"]
    robots = "noindex, nofollow" if (demo or p["url"] in NOINDEX) else "index, follow, max-image-preview:large"
    lines = [
        "<!-- Meta -->",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(s['title'])}</title>",
        f'<meta name="description" content="{esc(s["description"])}">',
        *([] if p["url"] == "/404" else [f'<link rel="canonical" href="{url}">']),
        f'<meta name="robots" content="{robots}">',
        '<meta property="og:type" content="{}">'.format("article" if p["type"] == "post" else "website"),
        '<meta property="og:site_name" content="AdEasy">',
        '<meta property="og:locale" content="en_CA">',
        f'<meta property="og:title" content="{esc(s["title"])}">',
        f'<meta property="og:description" content="{esc(s["description"])}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{og}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{esc(s["ogAlt"])}">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="theme-color" content="#1E2859">',
    ]
    if C.GSC_VERIFICATION and p["url"] == "/":
        lines.append(f'<meta name="google-site-verification" content="{esc(C.GSC_VERIFICATION)}">')
    lines += [
        "<!-- Favicon -->",
        '<link rel="icon" href="/favicon.ico" sizes="48x48">',
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        '<link rel="manifest" href="/site.webmanifest">',
        "<!-- Fonts -->",
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        f'<link rel="stylesheet" href="{FONTS}">',
    ]
    if hero:
        v = hero["variants"]
        srcset = ", ".join(f"/assets/img/{x['avif']} {x['w']}w" for x in v)
        sizes = f"(max-width: 680px) {hero['m'] or 92}px, {hero['d'] or hero['w']}px"
        if hero.get("mobile"):  # art-directed hero: preload the right crop for each screen size
            mv = hero["mobile"]
            msrc = ", ".join(f"/assets/img/{x['avif']} {x['w']}w" for x in mv["variants"])
            lines.append(f'<link rel="preload" as="image" type="image/avif" media="(max-width: 680px)" imagesrcset="{msrc}" imagesizes="{mv["m"] or 92}px" fetchpriority="high">')
            lines.append(f'<link rel="preload" as="image" type="image/avif" media="(min-width: 681px)" imagesrcset="{srcset}" imagesizes="{hero["d"] or hero["w"]}px" fetchpriority="high">')
        else:
            lines.append(f'<link rel="preload" as="image" type="image/avif" imagesrcset="{srcset}" imagesizes="{sizes}" fetchpriority="high">')
    lines += [
        "<!-- Critical CSS -->",
        "<style>" + CRITICAL + "</style>",
        "<!-- Stylesheets -->",
    ]
    for css in ("base", "layout", "components", "pages"):
        lines.append(f'<link rel="stylesheet" href="/assets/css/{css}.css?v={ASSET_V("css/" + css + ".css")}" media="print" onload="this.media=\'all\'">')
    lines.append("<noscript>" + "".join(f'<link rel="stylesheet" href="/assets/css/{c}.css?v={ASSET_V("css/" + c + ".css")}">' for c in ("base", "layout", "components", "pages")) + "</noscript>")
    if C.GTM_ID and not demo:
        lines += ["<!-- Tracking -->", GTM_SNIPPET.replace("GTM_ID", C.GTM_ID).replace("GTM_DELAY", str(C.GTM_DELAY_MS))]
    lines += ["<!-- Schema -->", '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False) + "</script>"]
    return "\n".join(lines)


GTM_SNIPPET = """<script>
/* GTM loads on the visitor's first interaction, or GTM_DELAY ms after the page finishes loading.
   Tradeoff: a visitor who leaves before either happens is not counted. */
window.dataLayer = window.dataLayer || [];
(function () {
  var done = false;
  function load() {
    if (done) return; done = true;
    window.dataLayer.push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });
    var s = document.createElement('script'); s.async = true;
    s.src = 'https://www.googletagmanager.com/gtm.js?id=GTM_ID';
    document.head.appendChild(s);
  }
  ['pointerdown', 'keydown', 'scroll', 'touchstart'].forEach(function (e) { window.addEventListener(e, load, { once: true, passive: true }); });
  window.addEventListener('load', function () { setTimeout(load, GTM_DELAY); });
})();
</script>"""

CRITICAL = ""  # filled in main() from the top of layout.css plus the font and colour tokens


def build_critical():
    base = open(os.path.join(ROOT, "assets/css/base.css")).read()
    tokens = re.search(r":root\s*\{.*?\n\}", base, re.S).group(0)
    tokens = re.sub(r"/\*.*?\*/", "", tokens, flags=re.S)
    layout = open(os.path.join(ROOT, "assets/css/layout.css")).read()
    frame = layout.split("/* ---- Footer ---- */")[0]
    frame = re.sub(r"/\*.*?\*/", "", frame, flags=re.S)
    # blocks.css (containers, heroes, section labels, type styles) is small and used above the fold
    # on every page, so it ships inline rather than as a separate request.
    blocks = re.sub(r"/\*.*?\*/", "", open(os.path.join(ROOT, "assets/css/blocks.css")).read(), flags=re.S)
    css = tokens + frame + blocks
    css = re.sub(r"\s*\n\s*", "", css)
    css = re.sub(r"\s{2,}", " ", css)
    return css


# ---------- Page assembly ----------

def build_page(p, demo):
    name = p["name"]
    m = META[name]
    body_src = open(os.path.join(SRC, "pages", name + ".html")).read()
    hdr = PARTIAL("header.html")
    if p["nav"]:
        hdr = hdr.replace(f'class="nav-link" data-nav="{p["nav"]}"', f'class="nav-link is-active" data-nav="{p["nav"]}"')
    footer = ("<!-- PARTIAL: assessment CTA. Edit _source/partials/cta-assessment.html, not here -->\n" + PARTIAL("cta-assessment.html")
              if m["cta"] else "")
    footer += "<!-- PARTIAL: footer. Edit _source/partials/footer.html, not here -->\n" + PARTIAL("footer.html")
    doc = BeautifulSoup(
        "<!DOCTYPE html>\n<html lang=\"en-CA\"><head></head><body>"
        "<!-- PARTIAL: header. Edit _source/partials/header.html, not here -->\n" + hdr +
        f'<main id="main" class="page" style="{m["wrapperStyle"]}">\n' + body_src + "</main>\n" + footer +
        "</body></html>", "html.parser")
    main = doc.find("main")
    # images
    hero = None
    for i, img in enumerate(main.find_all("img")):
        mm = picture(img, eager=(i == 0 and p["type"] != "post" or (i == 0 and p["type"] == "post")))
        if i == 0 and mm and not mm.get("svg"):
            hero = mm
    for img in doc.select("header img, footer img, #marketing-assessment img, [id^=marketing-assessment] img"):
        if img.find_parent("picture") is None:
            picture(img, eager=bool(img.find_parent("header")))
    for img in doc.find_all("img"):
        if img.find_parent("picture") is None and img.get("src", "").startswith("/assets/img/"):
            picture(img)
    # forms
    has_form = False
    for f in main.find_all("form", attrs={"data-form": True}):
        has_form = True
        f["data-endpoint"] = C.FORM_ENDPOINT
        hp = doc.new_tag("div", attrs={"class": "form-hp", "aria-hidden": "true"})
        hp.append(BeautifulSoup('<label>Leave this field empty <input type="text" name="website" tabindex="-1" autocomplete="off"></label>', "html.parser"))
        f.insert(0, hp)
        if C.TURNSTILE_SITEKEY and not demo:
            btn = f.find(attrs={"type": "submit"})
            ts = doc.new_tag("div", attrs={"class": "cf-turnstile", "data-sitekey": C.TURNSTILE_SITEKEY, "data-action": re.sub(r"\W+", "_", f["data-form"].lower())})
            btn.insert_before(ts)
    # labels: give each control a unique id and point its label at it
    n = 0
    for lab in main.find_all("label"):
        ctl = lab.find(["input", "textarea", "select"])
        if ctl and not lab.get("for"):
            n += 1
            cid = ctl.get("id") or f"f-{ctl.get('name', 'field')}-{n}"
            ctl["id"] = cid
            lab["for"] = cid
    # head
    schema = schema_for(p, main)
    doc.head.append(BeautifulSoup(head(p, schema, demo, hero), "html.parser"))
    # scripts
    scripts = [f'<script src="/assets/js/site.js?v={ASSET_V("js/site.js")}" defer></script>']
    if has_form:
        scripts.append(f'<script src="/assets/js/forms.js?v={ASSET_V("js/forms.js")}" defer></script>')
        if C.TURNSTILE_SITEKEY and not demo:
            scripts.append('<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>')
    doc.body.append(BeautifulSoup("\n".join(scripts), "html.parser"))
    # footer landmark
    ft = doc.find(id="footer")
    if ft:
        ft.name = "footer"
        ft["class"] = (ft.get("class") or []) + ["site-footer"]
    return doc


def relativize(doc, page_file):
    """Demo build: turn /abs links into relative .html paths that work on any host."""
    here = posixpath.dirname(page_file)

    def rel(u):
        if not u.startswith("/") or u.startswith("//"):
            return u
        path, _, frag = u.partition("#")
        if path.startswith("/assets/") or re.search(r"\.[a-z0-9]{2,5}$", path):
            target = path.lstrip("/")
        elif path in URL_TO_NAME:
            target = "home.html" if path == "/" else out_file(path)
        else:
            target = path.lstrip("/") + ".html"
        r = posixpath.relpath(target, here or ".")
        return r + ("#" + frag if frag else "")

    for t in doc.find_all(True):
        for a in ("href", "src", "action", "data-full"):
            if t.get(a):
                t[a] = rel(t[a])
        for a in ("srcset", "imagesrcset"):
            if t.get(a):
                t[a] = ", ".join(" ".join([rel(x.split()[0])] + x.split()[1:]) for x in t[a].split(", "))
        if t.name == "link" and t.get("rel") == ["canonical"]:
            continue
    # demo: fallback images only (keeps the artifact under its file limit)
    for s in doc.find_all("source"):
        if s.get("type", "").startswith("image/"):
            s.decompose()
    for img in doc.find_all("img"):
        if img.get("srcset"):
            del img["srcset"]
            if img.get("sizes"):
                del img["sizes"]
    # The review viewer keeps the scroll position between pages; start each page at the top.
    doc.html["data-demo"] = ""
    doc.head.append(BeautifulSoup('<script>(function(){if(location.hash)return;try{history.scrollRestoration="manual"}catch(e){}var t0=Date.now(),user=false;function top(){if(!user&&Date.now()-t0<2500&&window.scrollY>0)window.scrollTo(0,0)}["wheel","touchstart","keydown","pointerdown"].forEach(function(e){addEventListener(e,function(){user=true},{once:true,passive:true})});addEventListener("scroll",top,{passive:true});addEventListener("load",top);[0,50,150,400,900,1600].forEach(function(d){setTimeout(top,d)})})();</script>', "html.parser"))
    for l in doc.find_all("link", rel="preload"):
        l.decompose()
    for l in doc.find_all("link"):
        if l.get("media") == "print":
            l["media"] = "all"
            del l["onload"]


def serialize(doc):
    s = str(doc)
    s = s.replace("<!DOCTYPE html>\n", "<!DOCTYPE html>\n", 1)
    return s


def main():
    global CRITICAL
    demo = "--demo" in sys.argv
    out = sys.argv[sys.argv.index("--demo") + 1] if demo else ROOT
    CRITICAL = build_critical()
    written = []
    for row in PAGES:
        p = dict(zip(("url", "name", "nav", "type", "parent"), row))
        doc = build_page(p, demo)
        f = out_file(p["url"])
        if demo:
            f = "home.html" if p["url"] == "/" else f
            relativize(doc, f)
        dst = os.path.join(out, f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w").write(serialize(doc))
        written.append(f)
    if not demo:
        write_sitemap(out)
    print(f"{len(written)} pages written to {out}")


def write_sitemap(out):
    """sitemap.xml from the same page list as the canonicals, so the two can never disagree."""
    rows = []
    for (url, name, *_r) in PAGES:
        if url in NOINDEX:
            continue
        rows.append(f"  <url><loc>{abs_url(url)}</loc><lastmod>{SEO[url].get('lastmod', TODAY)}</lastmod></url>")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n"
    open(os.path.join(out, "sitemap.xml"), "w").write(xml)


if __name__ == "__main__":
    main()
