#!/usr/bin/env python3
"""Draw the panels the build found, so you can check them at a glance.

Each strip or page gets a coloured box per panel, numbered in reading order.
It reads the built data, so run tools/build.py first.

Usage:  python3 tools/show_panels.py primate-suspects                  every page
        python3 tools/show_panels.py primate-suspects 9-16             pages 9 to 16
        python3 tools/show_panels.py tom-waits 15 16 --out panels.png

Page numbers are the reader's, as in a link like #tom-waits/p15.
Needs Pillow.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
COLOURS = [(255, 0, 60), (0, 220, 255), (60, 255, 60), (255, 200, 0), (200, 80, 255), (255, 255, 255)]


def wanted_pages(specs, count):
    if not specs:
        return list(range(1, count + 1))
    out = []
    for spec in specs:
        a, _, b = spec.partition("-")
        out += range(int(a), int(b or a) + 1)
    return [n for n in out if 1 <= n <= count]


def main():
    ap = argparse.ArgumentParser(description="Draw the detected panels for a comic.")
    ap.add_argument("comic")
    ap.add_argument("pages", nargs="*", help="page numbers or ranges, such as 3 or 9-16 (default: all)")
    ap.add_argument("--out", help="image to write (default: panels-<comic>.png)")
    ap.add_argument("--width", type=int, default=480, help="width of each page in the sheet")
    args = ap.parse_args()

    data = ROOT / "comics" / args.comic / "comic.json"
    if not data.exists():
        sys.exit(f"No built data at {data.relative_to(ROOT)}. Run: python3 tools/build.py {args.comic}")
    comic = json.loads(data.read_text())
    pages = [comic["pages"][n - 1] for n in wanted_pages(args.pages, len(comic["pages"]))]
    pages = [p for p in pages if p["kind"] in ("strip", "page")] or pages

    tiles = []
    for p in pages:
        s = args.width / p["w"]
        im = Image.open(ROOT / p["src"].split("?")[0]).convert("RGB")
        im = im.resize((args.width, round(p["h"] * s)), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        for f in p["frames"]:
            if f.get("intro") or p["kind"] not in ("strip", "page"):
                continue
            x, y, w, h = [v * s for v in f["rect"]]
            d.rectangle([x + 2, y + 2, x + w - 3, y + h - 3], outline=COLOURS[(f["n"] - 1) % 6], width=3)
            d.rectangle([x + 5, y + 5, x + 21, y + 23], fill=(0, 0, 0))
            d.text((x + 9, y + 8), str(f["n"]), fill=(255, 255, 255))
        d.rectangle([0, 0, 34, 16], fill=(0, 0, 0))
        d.text((4, 2), f"p{int(p['id'])}", fill=(255, 255, 0))
        tiles.append(im)

    cols = 4 if tiles and tiles[0].height > tiles[0].width else 3
    pad = 6
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    sheet = Image.new("RGB", (min(cols, len(tiles)) * (args.width + pad) + pad,
                              sum(max(t.height for t in r) + pad for r in rows) + pad), (40, 40, 40))
    y = pad
    for r in rows:
        for k, t in enumerate(r):
            sheet.paste(t, (pad + k * (args.width + pad), y))
        y += max(t.height for t in r) + pad
    out = Path(args.out or f"panels-{args.comic}.png")
    sheet.save(out)
    print(f"Wrote {out} with {len(tiles)} page(s)")


if __name__ == "__main__":
    main()
