#!/usr/bin/env python3
"""Comic overlays for the animation: speech balloons, sound-effect lettering,
caption boxes and the series masthead, rendered as an RGBA frame sequence
and composited over a cut with ffmpeg.

The balloon is a port of the Monsters Undone speech effect
(music-visualization-toolkit/projects/monsters-loose, HARPER-SPEECH-001
build v005): one continuous hand-shaped contour with the curved tail part of
the same perimeter, ivory paper fill, a weighted ink outline whose pressure
varies around the perimeter, Bangers lettering at constant size, the balloon
inflating as the first word lands and the other words arriving at stable
positions, a small settle, a five-frame ease in and a four-frame fade out.

    python animation/tools/overlays.py SPEC.json --frame 3.2 OUT.png     # one frame, for review
    python animation/tools/overlays.py SPEC.json --render FRAMES_DIR      # ov-%05d.png for the whole cut
    python animation/tools/overlays.py SPEC.json --composite BASE.mp4 OUT.mp4

SPEC.json:
{
 "fps": 24, "size": [1920, 1080], "duration": 49.0,
 "font": "../tools/fonts/Bangers-Regular.ttf",
 "elements": [
  {"type": "bubble", "start": 3.2, "end": 5.6, "lines": ["TEN TIMES", "THE CAFFEINE!"],
   "center": [640, 190], "tip": [621, 384], "size": 42},
  {"type": "sfx", "start": 30.1, "end": 31.0, "text": "squeak", "center": [1100, 760],
   "angle": -14, "size": 72, "source": [1150, 700]},
  {"type": "caption", "start": 24.0, "end": 27.0, "text": "FOUR HOURS LATER", "pos": [48, 44], "size": 44},
  {"type": "masthead", "start": 0.0, "end": 3.0, "title": "THE PRIMATE SUSPECTS",
   "subtitle": "UNDER PRESSURE", "y": 70}
 ]
}
Times are seconds in the cut; positions are pixels in the output frame.
"""
import json
import math
import pathlib
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

SS = 2  # supersampling factor for anti-aliased edges
INK = (6, 8, 7, 255)
PAPER = (240, 224, 176, 255)
YELLOW = (250, 205, 48, 255)
RED = (184, 28, 30, 255)
TEAL = (22, 70, 88, 255)
WHITE = (246, 240, 226, 255)


def smooth(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class Fonts:
    def __init__(self, path: str):
        self.path = path
        self.cache: dict[int, ImageFont.FreeTypeFont] = {}

    def get(self, size: int) -> ImageFont.FreeTypeFont:
        px = int(round(size * SS))
        if px not in self.cache:
            self.cache[px] = ImageFont.truetype(self.path, px)
        return self.cache[px]


def contour_points(a: float, b: float, phase: float, n: int = 120) -> list[tuple[float, float]]:
    """Hand-wobbled ellipse with half-axes a, b (unit scale), centred on 0."""
    pts = []
    for j in range(n):
        th = 2 * math.pi * j / n
        r = 1 + 0.025 * math.sin(3 * th + phase) + 0.015 * math.sin(5 * th + 1.3 + phase)
        pts.append((a * r * math.cos(th), b * r * math.sin(th)))
    return pts


def bezier(p0, p1, p2, p3, n=16):
    out = []
    for j in range(n):
        t = j / n
        out.append(tuple((1 - t) ** 3 * p0[k] + 3 * (1 - t) ** 2 * t * p1[k] + 3 * (1 - t) * t * t * p2[k]
                         + t ** 3 * p3[k] for k in (0, 1)))
    return out


def balloon_polygon(cx, cy, a, b, tip, phase):
    """Continuous perimeter: wobbled body plus a curved tail that reaches `tip`."""
    tx, ty = tip[0] - cx, tip[1] - cy
    th_t = math.atan2(ty / max(b, 1), tx / max(a, 1))      # tail direction in ellipse space
    delta = 0.30
    body = []
    n = 120
    for j in range(n + 1):
        th = th_t + delta + (2 * math.pi - 2 * delta) * j / n
        r = 1 + 0.025 * math.sin(3 * th + phase) + 0.015 * math.sin(5 * th + 1.3 + phase)
        body.append((cx + a * r * math.cos(th), cy + b * r * math.sin(th)))
    p_end = body[-1]      # at th_t - delta
    p_start = body[0]     # at th_t + delta
    # Tail: two curves bowed to the same side so the tail bends like a brush stroke.
    dist = math.hypot(tx, ty)
    side = (-ty / max(dist, 1), tx / max(dist, 1))
    bow = 0.22 * dist
    tipp = (tip[0], tip[1])
    c1 = (p_end[0] + (tipp[0] - p_end[0]) * 0.45 + side[0] * bow, p_end[1] + (tipp[1] - p_end[1]) * 0.45 + side[1] * bow)
    c2 = (p_start[0] + (tipp[0] - p_start[0]) * 0.55 + side[0] * bow, p_start[1] + (tipp[1] - p_start[1]) * 0.55 + side[1] * bow)
    tail_out = bezier(p_end, c1, c1, tipp, 14)
    tail_back = bezier(tipp, c2, c2, p_start, 14)
    return body + tail_out + tail_back


def ribbon(pts, base_w):
    """Outline polygon (outer path + reversed inner path) with varying pen pressure."""
    n = len(pts)
    outer, inner = [], []
    for j, (x, y) in enumerate(pts):
        px, py = pts[(j - 1) % n]
        nx_, ny_ = pts[(j + 1) % n]
        tx, ty = nx_ - px, ny_ - py
        ln = max(0.001, math.hypot(tx, ty))
        nx, ny = -ty / ln, tx / ln
        u = 2 * math.pi * j / n
        w = base_w * (1 + 0.22 * math.sin(u * 3 + 0.7) + 0.12 * math.sin(u * 7 + 1.3))
        outer.append((x + nx * w, y + ny * w))
        inner.append((x - nx * w, y - ny * w))
    return outer + inner[::-1]


def draw_text(draw, xy, text, font, fill, stroke=0, stroke_fill=None, anchor="mm"):
    draw.text(xy, text, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill, anchor=anchor)


# ---------------------------------------------------------------- elements

def render_bubble(img, el, t, fps, fonts):
    f = (t - el["start"]) * fps
    total = (el["end"] - el["start"]) * fps
    if f < 0 or f > total:
        return
    size = el.get("size", 42)
    font = fonts.get(size)
    lines = el["lines"]
    gap = size * 0.28 * SS
    line_h = size * 1.08 * SS
    rows = []
    for line in lines:
        words = line.split()
        widths = [font.getlength(w) for w in words]
        rows.append((words, widths, sum(widths) + gap * (len(words) - 1)))
    text_w = max(r[2] for r in rows)
    text_h = line_h * len(lines)
    pad_x, pad_y = size * 0.95 * SS, size * 0.62 * SS
    A, B = text_w / 2 + pad_x, text_h / 2 + pad_y
    cx, cy = el["center"][0] * SS, el["center"][1] * SS
    tip = (el["tip"][0] * SS, el["tip"][1] * SS)
    # Inflation: starts just wide enough for the first word, grows with it.
    first_w = rows[0][1][0]
    initial = max(0.34, (first_w + pad_x * 1.2) / (2 * A))
    # Word schedule first (the balloon's growth is paced to it): the Monsters
    # rhythm (six frames apart on the first line, four on the rest) unless the
    # bubble is short, in which case the whole text has landed by ~45% of its life.
    n_words = sum(len(r[0]) for r in rows)
    budget = max(6.0, 0.45 * total - 2)
    sp = min(6.0, budget / max(1, n_words)) if n_words > 1 else 6.0
    sp_first, sp_rest = sp, min(4.0, sp)
    n0 = len(rows[0][0])
    row0_done = 2 + (n0 - 1) * sp_first
    arrivals = []
    k = 0
    for li, (words, widths, total_w) in enumerate(rows):
        row = []
        for wi in range(len(words)):
            row.append(2 + wi * sp_first if li == 0 else row0_done + 4 + (k - n0) * sp_rest)
            k += 1
        arrivals.append(row)
    # Width grows as the first line fills; height grows once the first line is
    # complete, so the next line always lands inside paper.
    gdur = min(7.0, max(3.0, sp_first + 1))
    gx = smooth((f - 2) / gdur)
    gy = smooth((f - max(4.0, row0_done)) / 6) if len(rows) > 1 else smooth((f - 2) / gdur)
    word_gx = max(gx, smooth((f - 2) / max(1.0, sp_first - 0.5)))
    settle = 0.01 * math.sin(math.pi * (f - 20) / 8) if 20 <= f <= 28 else 0
    ax = (initial + (1 - initial) * gx) * (1 + settle)
    ay = (0.56 + 0.44 * gy) * (1 + settle)
    dx = 0.004 * A * math.sin(f * 0.06)
    dy = 0.004 * B * math.sin(f * 0.045)
    poly = balloon_polygon(cx + dx, cy + dy, A * ax, B * ay, tip, el.get("phase", 0.4))
    # Opacity: five-frame ease in, four-frame fade out.
    u = min(1.0, (f + 1) / 5, (total - f + 1) / 4)
    alpha = smooth(u)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.polygon(poly, fill=PAPER)
    d.polygon(ribbon(poly, size * 0.075 * SS), fill=INK)
    for li, (words, widths, total_w) in enumerate(rows):
        offset = -total_w / 2
        # The first line starts in the middle of the young balloon and rises to
        # its slot as the balloon grows; later lines sit in their final slots.
        slot = (li - (len(lines) - 1) / 2) * line_h
        y = cy + dy + (slot * gy if li == 0 else slot)
        for wi, (word, w) in enumerate(zip(words, widths)):
            arrival = arrivals[li][wi]
            if f < arrival:
                offset += w + gap
                continue
            if li == 0 and wi == 0:
                x = cx + dx + (-first_w / 2 + (offset + first_w / 2) * word_gx)
            else:
                x = cx + dx + offset
            draw_text(d, (x, y), word, font, INK, anchor="lm")
            offset += w + gap
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(layer)


def render_sfx(img, el, t, fps, fonts):
    f = (t - el["start"]) * fps
    total = (el["end"] - el["start"]) * fps
    if f < 0 or f > total:
        return
    size = el.get("size", 72)
    # Pop: 0.55 -> 1.12 -> 1.0 over six frames.
    if f < 3:
        sc = 0.55 + 0.57 * smooth(f / 3)
    elif f < 6:
        sc = 1.12 - 0.12 * smooth((f - 3) / 3)
    else:
        sc = 1.0
    alpha = smooth(min(1.0, (f + 1) / 2, (total - f + 1) / 4))
    font = fonts.get(int(size * sc))
    text = el["text"]
    cx, cy = el["center"][0] * SS, el["center"][1] * SS
    # Lettering on its own layer so it can be rotated.
    w = int(font.getlength(text) + size * SS)
    h = int(size * sc * SS * 1.6)
    tile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    draw_text(td, (w / 2, h / 2), text, font, INK, stroke=int(size * 0.07 * SS), stroke_fill=PAPER)
    tile = tile.rotate(el.get("angle", -12), resample=Image.BICUBIC, expand=True)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # Emanata: short radiating lines from the sound source, flickering slightly.
    if "source" in el:
        sx, sy = el["source"][0] * SS, el["source"][1] * SS
        ang0 = math.atan2(cy - sy, cx - sx)
        for k in range(el.get("rays", 4)):
            a = ang0 + (k - 1.5) * 0.42 + 0.06 * math.sin(f * 0.9 + k)
            r0 = size * SS * (0.35 + 0.05 * ((f + k) % 3))
            r1 = r0 + size * SS * 0.55 * sc
            d.line([(sx + r0 * math.cos(a), sy + r0 * math.sin(a)), (sx + r1 * math.cos(a), sy + r1 * math.sin(a))],
                   fill=INK, width=int(size * 0.06 * SS))
    layer.alpha_composite(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)))
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(layer)


def render_caption(img, el, t, fps, fonts):
    f = (t - el["start"]) * fps
    total = (el["end"] - el["start"]) * fps
    if f < 0 or f > total:
        return
    size = el.get("size", 44)
    font = fonts.get(size)
    text = el["text"]
    slide = 1 - smooth(f / 8)                   # slides in from the left over eight frames
    alpha = smooth(min(1.0, (f + 1) / 3, (total - f + 1) / 5))
    x0, y0 = el["pos"][0] * SS, el["pos"][1] * SS
    pad_x, pad_y = size * 0.55 * SS, size * 0.32 * SS
    tw = font.getlength(text)
    th = size * 1.0 * SS
    bw, bh = tw + 2 * pad_x, th + 2 * pad_y
    x0 -= slide * (bw + x0)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    border = int(size * 0.075 * SS)
    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=(247, 232, 150, 255), outline=INK, width=border)
    draw_text(d, (x0 + bw / 2, y0 + bh / 2 + size * 0.04 * SS), text, font, INK, anchor="mm")
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(layer)


def render_masthead(img, el, t, fps, fonts):
    f = (t - el["start"]) * fps
    total = (el["end"] - el["start"]) * fps
    if f < 0 or f > total:
        return
    W = img.size[0]
    size = el.get("size", 92)
    sub_size = el.get("sub_size", 46)
    font = fonts.get(size)
    sub = fonts.get(sub_size)
    title, subtitle = el["title"], el.get("subtitle", "")
    band_h = size * 1.45 * SS
    y = el.get("y", 70) * SS
    enter = smooth(f / 10)
    leave = smooth((f - (total - 10)) / 10) if f > total - 10 else 0
    yy = y - (1 - enter) * (band_h + y) - leave * (band_h + y)
    margin = el.get("margin", 110) * SS
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([margin, yy, W - margin, yy + band_h], radius=size * 0.25 * SS, fill=TEAL,
                        outline=(10, 36, 46, 255), width=int(size * 0.05 * SS))
    tw = font.getlength(title)
    sw = sub.getlength(subtitle) if subtitle else 0
    divider = size * 0.9 * SS if subtitle else 0
    total_w = tw + divider + sw
    x = (W - total_w) / 2
    # Title: yellow with a red outline, sheared a little for the comic slant.
    tile_w, tile_h = int(tw + size * SS), int(band_h)
    tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    draw_text(td, (tile_w / 2, tile_h / 2 + size * 0.05 * SS), title, font, YELLOW,
              stroke=int(size * 0.06 * SS), stroke_fill=RED)
    shear = 0.14
    tile = tile.transform(tile.size, Image.AFFINE, (1, shear, -shear * tile_h / 2, 0, 1, 0), resample=Image.BICUBIC)
    layer.alpha_composite(tile, (int(x - size * SS / 2), int(yy)))
    if subtitle:
        dx = x + tw + divider / 2
        d.line([(dx, yy + band_h * 0.22), (dx, yy + band_h * 0.78)], fill=WHITE, width=int(size * 0.03 * SS))
        draw_text(d, (dx + divider / 2 + sw / 2, yy + band_h / 2 + sub_size * 0.08 * SS), subtitle, sub, WHITE, anchor="mm")
    img.alpha_composite(layer)


RENDERERS = {"bubble": render_bubble, "sfx": render_sfx, "caption": render_caption, "masthead": render_masthead}


def active(spec, t):
    return [e for e in spec["elements"] if e["start"] <= t <= e["end"]]


def render_frame(spec, t, fonts):
    w, h = spec.get("size", [1920, 1080])
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    for el in active(spec, t):
        RENDERERS[el["type"]](img, el, t, spec.get("fps", 24), fonts)
    return img.resize((w, h), Image.LANCZOS)


def resolve_times(spec, spec_path):
    """Elements with a "clip" key carry times relative to that clip's start in
    the cut; the timeline file written by assemble_cut.py supplies the offset."""
    if "timeline" not in spec:
        return
    tl = json.load(open(spec_path.parent / spec["timeline"], encoding="utf-8"))
    starts = {pathlib.Path(it["item"]).stem: it["start"] for it in tl}
    ends = {pathlib.Path(it["item"]).stem: it["start"] + it["sec"] for it in tl}
    for el in spec["elements"]:
        clip = el.get("clip")
        if not clip:
            continue
        if clip not in starts:
            raise SystemExit(f"clip {clip} not in timeline")
        el["start"] = starts[clip] + el["start"]
        el["end"] = (ends[clip] if el.get("end") == "end" else starts[clip] + el["end"])
    if "duration" not in spec:
        spec["duration"] = max(ends.values())


def main(argv):
    spec_path = pathlib.Path(argv[0])
    spec = json.load(open(spec_path, encoding="utf-8"))
    resolve_times(spec, spec_path)
    fonts = Fonts(str((spec_path.parent / spec["font"]).resolve()))
    fps = spec.get("fps", 24)
    if argv[1] == "--frame":
        t = float(argv[2])
        render_frame(spec, t, fonts).save(argv[3])
        print("wrote", argv[3], "active:", [e["type"] for e in active(spec, t)])
        return
    out_dir = pathlib.Path(argv[2] if argv[1] == "--render" else spec_path.parent / "_overlay_frames")
    out_dir.mkdir(parents=True, exist_ok=True)
    n = int(round(spec["duration"] * fps))
    w, h = spec.get("size", [1920, 1080])
    empty = out_dir / "_empty.png"
    Image.new("RGBA", (w, h), (0, 0, 0, 0)).save(empty)
    drawn = 0
    for i in range(n):
        t = i / fps
        dst = out_dir / f"ov-{i:05d}.png"
        if active(spec, t):
            render_frame(spec, t, fonts).save(dst)
            drawn += 1
        else:
            shutil.copyfile(empty, dst)
    print(f"rendered {drawn} drawn frames of {n} into {out_dir}")
    if argv[1] == "--composite":
        base, out = argv[2], argv[3]
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", base, "-framerate", str(fps),
               "-i", str(out_dir / "ov-%05d.png"),
               "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto:shortest=1[v]",
               "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
               "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", out]
        subprocess.run(cmd, check=True)
        print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1:])
