#!/usr/bin/env python3
"""Cut reference crops for the plate generator from a published page.

    python animation/tools/crop_panels.py EPISODE PAGE_ID OUT_DIR
    python animation/tools/crop_panels.py 09 10 animation/a-useful-man/plates/src

EPISODE is the two-digit prefix of the file in source-images-primate-suspects/,
PAGE_ID the page "id" in comics/primate-suspects/comic.json (cover is 01, so
episode N is page N+1). Frame rects in comic.json are in the 1024x1536 reader
space; the source PNG is the same size today but is scaled here in case that
changes. Also writes cover_major.png, the Major cut from the cover.
"""
import glob
import json
import pathlib
import subprocess
import sys


def size(path: str) -> tuple[int, int]:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
                                   "-of", "csv=p=0", path]).decode().strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)


def crop(src: str, rect: tuple[int, int, int, int], dst: pathlib.Path) -> None:
    x, y, w, h = rect
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src,
                    "-vf", f"crop={w}:{h}:{x}:{y}", str(dst)], check=True)


def main(episode: str, page_id: str, out_dir: str) -> None:
    comic = json.load(open("comics/primate-suspects/comic.json", encoding="utf-8"))
    page = next(p for p in comic["pages"] if p["id"] == page_id)
    src = glob.glob(f"source-images-primate-suspects/{episode}-*.png")[0]
    w, h = size(src)
    sx, sy = w / page["w"], h / page["h"]
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for f in page["frames"]:
        if f.get("intro"):
            continue
        x, y, fw, fh = f["rect"]
        name = f["title"].lower().replace(" ", "_").replace(".", "").replace(",", "")
        dst = out / f"ep{episode}_p{f['n']}_{name}.png"
        crop(src, (int(x * sx), int(y * sy), int(fw * sx), int(fh * sy)), dst)
        print(dst.name)
    cover = "source-images-primate-suspects/00-primate-suspects-cover.png"
    cw, _ = size(cover)
    s = cw / 1024
    crop(cover, (0, int(450 * s), int(300 * s), int(760 * s)), out / "cover_major.png")
    print("cover_major.png")


if __name__ == "__main__":
    main(*sys.argv[1:4])
