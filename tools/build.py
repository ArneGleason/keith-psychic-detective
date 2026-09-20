#!/usr/bin/env python3
"""Build the web-ready comic from source-images/.

Reads   tools/story.json      scene + frame names, page order, optional gutter overrides
Writes  pages/NN.jpg          optimised full pages (progressive JPEG)
        thumbs/NN.jpg         small thumbnails for the index
        comic.json            manifest with detected frame rectangles

Frames are found by looking for the cream-coloured gutters that run the full
height of each strip. A page can override detection with
"gutters": [[x0, x1], ...] in story.json (inner gutters only).

Usage:  pip install pillow numpy && python3 tools/build.py
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source-images"
PAD = 5            # px of cream kept around each detected panel
JPEG_QUALITY = 80
THUMB_W = 360


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


def main():
    story = json.loads((ROOT / "tools" / "story.json").read_text())
    (ROOT / "pages").mkdir(exist_ok=True)
    (ROOT / "thumbs").mkdir(exist_ok=True)
    scene_ix = {s["id"]: i for i, s in enumerate(story["scenes"])}
    frame_counter = {}
    pages = []
    total = 0
    for n, p in enumerate(story["pages"], 1):
        pid = f"{n:02d}"
        im = Image.open(SRC / p["file"]).convert("RGB")
        w, h = im.size
        names = p["frames"]
        if p["kind"] == "strip":
            gut, top, bottom = detect(np.asarray(im), p.get("gutters"))
            if len(gut) - 1 != len(names):
                raise SystemExit(f"{p['file']}: found {len(gut) - 1} panels, story.json names {len(names)}")
            y0 = max(0, top[1] + 1 - PAD)
            y1 = min(h, bottom[0] + PAD)
            rects = []
            for a, b in zip(gut, gut[1:]):
                x0 = max(0, a[1] + 1 - PAD)
                x1 = min(w, b[0] + PAD)
                rects.append([x0, y0, x1 - x0, y1 - y0])
        else:
            rects = [[0, 0, w, h]]
        scene = story["scenes"][scene_ix[p["scene"]]]
        frames = []
        for rect, name in zip(rects, names):
            k = frame_counter[p["scene"]] = frame_counter.get(p["scene"], 0) + 1
            frames.append({"rect": rect, "title": name, "n": k})
        out = ROOT / "pages" / f"{pid}.jpg"
        im.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        th = im.resize((THUMB_W, round(h * THUMB_W / w)), Image.LANCZOS)
        th.save(ROOT / "thumbs" / f"{pid}.jpg", "JPEG", quality=70, optimize=True, progressive=True)
        total += out.stat().st_size
        pages.append({"id": pid, "src": f"pages/{pid}.jpg", "thumb": f"thumbs/{pid}.jpg",
                      "w": w, "h": h, "kind": p["kind"], "scene": scene_ix[p["scene"]], "frames": frames})
        print(pid, p["kind"], f"{out.stat().st_size // 1024:>5} KB", [f["rect"] for f in frames])
    manifest = {k: story[k] for k in ("title", "subtitle", "issue")}
    manifest["scenes"] = [{"num": s.get("num"), "title": s["title"]} for s in story["scenes"]]
    manifest["pages"] = pages
    (ROOT / "comic.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"total pages: {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
