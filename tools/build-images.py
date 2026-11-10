# build-images.py: makes every web image the site serves from the originals in _source/img.
# Re-run after adding or replacing an image. Writes assets/img/ (fallbacks) and assets/img/opt/ (AVIF, WebP).
#
# Usage:  python3 tools/build-images.py <site-root>
#   Reads  <site-root>/_source/img/**          originals, already named per the naming rules
#          <site-root>/_source/image-sizes.json rendered widths per image (desktop d, phone m), in CSS px
#   Writes <site-root>/assets/img/<name>.<jpg|png>        fallback at full size, plus -<w> smaller copy
#          <site-root>/assets/img/opt/<name>-<w>.<avif|webp>
#          <site-root>/_source/image-manifest.json        what build-html.py needs to write <picture> tags
#
# Rules (from the launch guide): size to the largest rendered width x2, capped at 1600 px; one smaller
# size for phones; AVIF ~q50, WebP ~q75, compressed JPG/PNG fallback; EXIF (incl. GPS) stripped.

import json
import os
import sys

from PIL import Image

MAX_W = 1600
DEFAULT_W = 1200  # images that never render visibly (e.g. lightbox-only)
AVIF_Q = 50
WEBP_Q = 75
JPG_Q = 80


def has_alpha(im):
    return im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)


def save_set(im, base, out_dir, opt_dir, w, alpha, rel_name):
    """Save one width of an image in AVIF, WebP and the fallback format. Returns dict of rel paths."""
    h = round(im.height * w / im.width)
    r = im.resize((w, h), Image.LANCZOS) if w < im.width else im
    stem = os.path.splitext(rel_name)[0]
    files = {}
    if alpha:
        fb = f"{stem}-{w}.png" if w != im.width else f"{stem}.png"
        r.save(os.path.join(out_dir, fb), "PNG", optimize=True)
    else:
        fb = f"{stem}-{w}.jpg" if w != im.width else f"{stem}.jpg"
        r.convert("RGB").save(os.path.join(out_dir, fb), "JPEG", quality=JPG_Q, optimize=True, progressive=True)
    files["fallback"] = fb
    av = f"{stem}-{w}.avif"
    wp = f"{stem}-{w}.webp"
    os.makedirs(os.path.dirname(os.path.join(opt_dir, av)), exist_ok=True)
    r.save(os.path.join(opt_dir, av), "AVIF", quality=AVIF_Q)
    r.save(os.path.join(opt_dir, wp), "WEBP", quality=WEBP_Q, method=6)
    files["avif"] = "opt/" + av
    files["webp"] = "opt/" + wp
    return files, h


def main(root):
    src_dir = os.path.join(root, "_source", "img")
    out_dir = os.path.join(root, "assets", "img")
    opt_dir = os.path.join(out_dir, "opt")
    sizes = json.load(open(os.path.join(root, "_source", "image-sizes.json")))
    manifest = {}
    for dirpath, _, names in os.walk(src_dir):
        for n in sorted(names):
            rel = os.path.relpath(os.path.join(dirpath, n), src_dir)
            if rel.endswith(".svg"):
                os.makedirs(os.path.dirname(os.path.join(out_dir, rel)) or out_dir, exist_ok=True)
                with open(os.path.join(dirpath, n), "rb") as a, open(os.path.join(out_dir, rel), "wb") as b:
                    b.write(a.read())
                manifest[rel] = {"svg": True, "fallback": rel}
                continue
            im = Image.open(os.path.join(dirpath, n))
            im.load()
            alpha = has_alpha(im)
            im = im.convert("RGBA" if alpha else "RGB")  # drops EXIF/GPS and colour-profile junk
            s = sizes.get(rel, {"d": 0, "m": 0})
            big = max(s["d"], s["m"]) * 2 or DEFAULT_W
            if "gallery/" in rel:
                big = MAX_W  # gallery opens full size in the lightbox
            big = min(big, MAX_W, im.width)
            small = min(s["m"] * 2, im.width) if s["m"] else 0
            os.makedirs(os.path.dirname(os.path.join(out_dir, rel)) or out_dir, exist_ok=True)
            # The full-size fallback keeps the plain name so its URL never changes.
            if big < im.width:
                im = im.resize((big, round(im.height * big / im.width)), Image.LANCZOS)
            entry = {"w": im.width, "h": im.height, "variants": []}
            files, _ = save_set(im, rel, out_dir, opt_dir, im.width, alpha, rel)
            entry["fallback"] = files["fallback"]
            entry["variants"].append({"w": im.width, **files})
            if small and small < im.width * 0.8:
                files_s, _ = save_set(im, rel, out_dir, opt_dir, small, alpha, rel)
                entry["variants"].append({"w": small, **files_s})
            entry["d"], entry["m"] = s["d"], s["m"]
            manifest[rel] = entry
            print(f"{rel}: {entry['w']}x{entry['h']} -> {[v['w'] for v in entry['variants']]}")
    json.dump(manifest, open(os.path.join(root, "_source", "image-manifest.json"), "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
