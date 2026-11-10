# build-og.py: makes each page's 1200 x 630 social sharing image (og:image) and fills its alt text.
# Source: the page's first photo (its hero), cropped to 1.91:1. Pages without a photo use the branded
# default. Override a page's choice with "ogSource" (an _source/img path) in _source/seo.json.
#
#   python3 tools/build-og.py

import json
import os
import sys

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pages import PAGES  # noqa: E402
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "_source")
OUT = os.path.join(ROOT, "assets", "img", "og")
W, H = 1200, 630
NAVY, ORANGE = (30, 40, 89), (241, 96, 13)


def default_card():
    im = Image.new("RGB", (W, H), NAVY)
    logo = Image.open(os.path.join(SRC, "img", "adeasy-logo-cream.png")).convert("RGBA")
    lw = 640
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    im.paste(logo, ((W - lw) // 2, (H - logo.height) // 2), logo)
    ImageDraw.Draw(im).rectangle([0, H - 14, W, H], fill=ORANGE)
    return im


def crop(path, focus_y=0.4):
    im = Image.open(path).convert("RGB")
    r = W / H
    if im.width / im.height > r:
        nw = round(im.height * r)
        x = (im.width - nw) // 2
        im = im.crop((x, 0, x + nw, im.height))
    else:
        nh = round(im.width / r)
        y = max(0, min(im.height - nh, round(im.height * focus_y - nh / 2)))
        im = im.crop((0, y, im.width, y + nh))
    return im.resize((W, H), Image.LANCZOS)


def save(im, path):
    q = 82
    while True:
        im.save(path, "JPEG", quality=q, optimize=True, progressive=True)
        if os.path.getsize(path) < 200_000 or q <= 50:
            return
        q -= 6


def main():
    os.makedirs(OUT, exist_ok=True)
    seo = json.load(open(os.path.join(SRC, "seo.json")))
    meta = json.load(open(os.path.join(SRC, "pages", "meta.json")))
    save(default_card(), os.path.join(OUT, "adeasy-default-og.jpg"))
    names = {row[0]: row[1] for row in PAGES}
    for url, s in seo.items():
        name = names[url]
        src = s.get("ogSource") or (meta[name]["heroImage"].replace("/assets/img/", "") if meta[name]["heroImage"] else "")
        body = open(os.path.join(SRC, "pages", name + ".html")).read()
        alt = ""
        if src:
            m = BeautifulSoup(body, "lxml").find("img", src="/assets/img/" + src)
            alt = (m.get("alt") or "").strip() if m else ""
            if not alt:  # photo not on the page itself (e.g. its Success Stories card): use the alt it has elsewhere
                for other in os.listdir(os.path.join(SRC, "pages")):
                    if other.endswith(".html"):
                        m = BeautifulSoup(open(os.path.join(SRC, "pages", other)).read(), "lxml").find("img", src="/assets/img/" + src)
                        if m and m.get("alt"):
                            alt = m["alt"].strip()
                            break
        is_photo = src and not src.endswith((".svg",)) and "logo" not in src
        if is_photo:
            save(crop(os.path.join(SRC, "img", src)), os.path.join(OUT, f"{name}-og.jpg"))
            s["og"] = f"/assets/img/og/{name}-og.jpg"
            s["ogAlt"] = alt or s["h1"]
        else:
            s["og"] = "/assets/img/og/adeasy-default-og.jpg"
            s["ogAlt"] = "AdEasy logo on a navy background"
    json.dump(seo, open(os.path.join(SRC, "seo.json"), "w"), indent=1, ensure_ascii=False)
    print(len(os.listdir(OUT)), "og images")


if __name__ == "__main__":
    main()
