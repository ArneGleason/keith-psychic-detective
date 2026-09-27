#!/usr/bin/env python3
"""Build the web-ready comics from their source images.

Config   tools/library.json          shelf title, tagline and the order of the comics
         tools/stories/<id>.json     one per comic: source folder, scenes, frame names
Output   comics/index.json           the shelf
         comics/<id>/comic.json      pages, scenes and detected frame rectangles
         comics/<id>/pages/NN.jpg    optimised full pages (progressive JPEG)
         comics/<id>/thumbs/NN.jpg   small thumbnails for the index
         comics/<id>/cover.jpg       the cover at shelf size
         social.jpg                  link-preview image showing every cover

Frames are found by looking for the cream-coloured gutters that run the full
height of each strip. A page can override detection with
"gutters": [[x0, x1], ...] in its story file (inner gutters only).

Images in a comic's source folder that its story file does not list are added
at the end under "New Pages" with numbered frames, so new strips show up before
they have been named. List a file under "skip" to leave it out.

Usage:  pip install pillow numpy
        python3 tools/build.py            build every comic
        python3 tools/build.py <id> ...   rebuild only these comics
"""
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
OUT = ROOT / "comics"
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp"}
PAD = 5            # px of cream kept around each detected panel
JPEG_QUALITY = 80
THUMB_W = 360
COVER_W = 720
SOCIAL_SIZE = (1200, 630)


# ---------- frame detection ----------

def runs(mask, minlen=3):
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= minlen:
                out.append((start, i - 1))
            start = None
    if start is not None and len(mask) - start >= minlen:
        out.append((start, len(mask) - 1))
    return out


def cream_mask(rgb):
    a = rgb.astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r > 205) & (g > 190) & (b > 120) & (r - b < 110)


def detect(rgb, inner_override=None):
    """Return (col_gutters, top, bottom): gutters as (x0, x1) incl. outer margins."""
    h, w, _ = rgb.shape
    cream = cream_mask(rgb)
    col_frac = cream[int(h * .08):int(h * .92)].mean(axis=0)
    row_frac = cream[:, int(w * .08):int(w * .92)].mean(axis=1)
    cols = runs(col_frac > .8)
    rows = runs(row_frac > .8)
    left = next((c for c in cols if c[0] <= 2), (0, -1))
    right = next((c for c in cols if c[1] >= w - 3), (w, w - 1))
    inner = [c for c in cols if c[0] > 2 and c[1] < w - 3]
    if inner_override is not None:
        inner = [tuple(g) for g in inner_override]
    top = next((r for r in rows if r[0] <= 2), (0, -1))
    bottom = next((r for r in rows if r[1] >= h - 3), (h, h - 1))
    return [left, *inner, right], top, bottom


def panel_rects(rgb, override=None):
    h, w, _ = rgb.shape
    gut, top, bottom = detect(rgb, override)
    y0 = max(0, top[1] + 1 - PAD)
    y1 = min(h, bottom[0] + PAD)
    rects = []
    for a, b in zip(gut, gut[1:]):
        x0 = max(0, a[1] + 1 - PAD)
        rects.append([x0, y0, min(w, b[0] + PAD) - x0, y1 - y0])
    return rects


# ---------- helpers ----------

def natural_key(name):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def save_jpeg(im, path, quality):
    """Write a JPEG and return its site URL with a content hash for cache busting."""
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    data = buf.getvalue()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)
    rel = path.relative_to(ROOT).as_posix()
    return f"{rel}?v={hashlib.sha1(data).hexdigest()[:10]}", len(data)


def resize_w(im, width):
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)


# ---------- one comic ----------

def build_comic(cid):
    story_path = TOOLS / "stories" / f"{cid}.json"
    story = json.loads(story_path.read_text())
    src = ROOT / story["source"]
    out = OUT / cid
    listed = [p["file"] for p in story["pages"]]
    missing = [f for f in listed if not (src / f).is_file()]
    if missing:
        sys.exit(f"{cid}: listed in {story_path.name} but not found in {story['source']}/: {', '.join(missing)}")

    scenes = list(story["scenes"])
    page_cfgs = list(story["pages"])
    skip = set(story.get("skip", []))
    extra = sorted((f.name for f in src.iterdir()
                    if f.suffix.lower() in IMAGE_TYPES and f.name not in listed and f.name not in skip),
                   key=natural_key)
    if extra:
        print(f"  NOTE: {len(extra)} image(s) not named in {story_path.name} yet, "
              f"added at the end as New Pages: {', '.join(extra)}")
        scenes.append({"id": "_new", "title": "New Pages"})
        page_cfgs += [{"file": f, "kind": "auto", "scene": "_new"} for f in extra]

    scene_ix = {s["id"]: i for i, s in enumerate(scenes)}
    frame_counter, pages, written, total = {}, [], set(), 0
    for n, p in enumerate(page_cfgs, 1):
        pid = f"{n:02d}"
        im = Image.open(src / p["file"]).convert("RGB")
        w, h = im.size
        kind, names = p["kind"], p.get("frames")
        rects = [[0, 0, w, h]]
        if kind in ("strip", "auto"):
            found = panel_rects(np.asarray(im), p.get("gutters"))
            if kind == "auto":
                kind = "strip" if w > h and len(found) > 1 else "splash"
                names = [None] * (len(found) if kind == "strip" else 1)
            elif len(found) != len(names):
                sys.exit(f"{cid}: {p['file']}: found {len(found)} panels but {story_path.name} names "
                         f"{len(names)}. Fix the names or add a \"gutters\" override for this page.")
            if kind == "strip":
                rects = found

        frames = []
        for rect, name in zip(rects, names):
            k = frame_counter[p["scene"]] = frame_counter.get(p["scene"], 0) + 1
            frames.append({"rect": rect, "title": name or f"Frame {k}", "n": k})

        page_url, size = save_jpeg(im, out / "pages" / f"{pid}.jpg", JPEG_QUALITY)
        thumb_url, _ = save_jpeg(resize_w(im, THUMB_W), out / "thumbs" / f"{pid}.jpg", 70)
        written |= {f"pages/{pid}.jpg", f"thumbs/{pid}.jpg"}
        total += size
        if n == 1:
            cover = resize_w(im, COVER_W)
            cover_url, _ = save_jpeg(cover, out / "cover.jpg", 82)
            cover_size = cover.size
        pages.append({"id": pid, "src": page_url, "thumb": thumb_url, "w": w, "h": h,
                      "kind": kind, "scene": scene_ix[p["scene"]], "frames": frames})
        print(f"  {pid} {kind:<6} {size // 1024:>4} KB  {len(frames)} frame(s)  {p['file']}")

    for sub in ("pages", "thumbs"):
        for f in (out / sub).glob("*.jpg"):
            if f"{sub}/{f.name}" not in written:
                f.unlink()

    comic = {
        "id": cid,
        "title": story["title"],
        "subtitle": story.get("subtitle", ""),
        "issue": story.get("issue", ""),
        "status": story.get("status", "complete"),
        "cover": cover_url, "coverW": cover_size[0], "coverH": cover_size[1],
        "scenes": [{"num": s.get("num"), "title": s["title"]} for s in scenes],
        "pages": pages,
    }
    (out / "comic.json").write_text(json.dumps(comic, indent=1, ensure_ascii=False) + "\n")
    print(f"  {len(pages)} pages, {sum(len(p['frames']) for p in pages)} frames, {total / 1e6:.1f} MB")
    return comic


# ---------- the shelf ----------

def shelf_entry(comic):
    strips = [p for p in comic["pages"] if p["kind"] == "strip"]
    return {k: comic[k] for k in ("id", "title", "subtitle", "issue", "status", "cover", "coverW", "coverH")} | {
        "strips": len(strips),
        "frames": sum(len(p["frames"]) for p in strips),
    }


def build_social(entries):
    """A 1200x630 link-preview image with every cover side by side."""
    W, H = SOCIAL_SIZE
    top, bottom = np.array([44, 30, 22]), np.array([14, 11, 10])
    t = np.linspace(0, 1, H)[:, None, None]
    canvas = Image.fromarray(np.broadcast_to(top + (bottom - top) * t, (H, W, 3)).astype(np.uint8))
    covers = [Image.open(ROOT / e["cover"].split("?")[0]).convert("RGB") for e in entries]
    ch, gap = 540, 44
    widths = [round(c.width * ch / c.height) for c in covers]
    span = sum(widths) + gap * (len(covers) - 1)
    if span > W - 80:
        f = (W - 80) / span
        ch, gap, widths = round(ch * f), round(gap * f), [round(x * f) for x in widths]
        span = sum(widths) + gap * (len(covers) - 1)
    x, y = (W - span) // 2, (H - ch) // 2
    shadow = Image.new("L", (W, H), 0)
    for cw in widths:
        shadow.paste(150, (x + 8, y + 12, x + cw + 8, y + ch + 12))
        x += cw + gap
    canvas.paste((0, 0, 0), mask=shadow.filter(ImageFilter.GaussianBlur(14)))
    x = (W - span) // 2
    for c, cw in zip(covers, widths):
        canvas.paste(c.resize((cw, ch), Image.LANCZOS), (x, y))
        x += cw + gap
    url, _ = save_jpeg(canvas, ROOT / "social.jpg", 85)
    return url


def main(argv):
    library = json.loads((TOOLS / "library.json").read_text())
    ids = library["comics"]
    unknown = [c for c in argv if c not in ids]
    if unknown:
        sys.exit(f"Unknown comic(s): {', '.join(unknown)}. Known: {', '.join(ids)}")
    wanted = set(argv or ids)
    comics = {}
    for cid in ids:
        existing = OUT / cid / "comic.json"
        if cid in wanted or not existing.exists():
            print(f"{cid}:")
            comics[cid] = build_comic(cid)
        else:
            comics[cid] = json.loads(existing.read_text())
    shelf = {"title": library["title"], "tagline": library["tagline"],
             "comics": [shelf_entry(comics[c]) for c in ids]}
    (OUT / "index.json").write_text(json.dumps(shelf, indent=1, ensure_ascii=False) + "\n")
    build_social(shelf["comics"])
    print(f"shelf: {', '.join(ids)}")


if __name__ == "__main__":
    main(sys.argv[1:])
