#!/usr/bin/env python3
"""Rebuild the README images from the real reader.

  hero    screenshots/hero.jpg    a strip on a laptop and a frame on a phone
  phones  screenshots/phones.jpg  the shelf, the index and the page after the last strip
  slide   screenshots/slide.gif   frame mode sliding along a strip, with motion blur

The page's clock is frozen with Playwright so the controls never fade out
mid-capture, and the slide is stepped 30 ms at a time for the animation.

Usage:  python3 tools/readme_screenshots.py              all three
        python3 tools/readme_screenshots.py phones       just the phones, after a new comic or a new count
        python3 tools/readme_screenshots.py --out /tmp/x write somewhere else to compare first

Needs:  pip install pillow numpy playwright   It uses your installed Google Chrome. Without
        Chrome, also run "python3 -m playwright install chromium" once.
"""
import argparse
import datetime as dt
import functools
import http.server
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
T0 = dt.datetime(2026, 9, 26, 20, 0, 0)
SS = 4  # supersampling for smooth rounded corners

# What each image shows. Change these to feature other comics.
HERO_LAPTOP = "captain-beefheart/p24"
HERO_PHONE = "keith-richards/p4f1"
PHONES_INDEX = "captain-beefheart/p20f1"
PHONES_LAST = "captain-beefheart/p45f1"
SLIDE_FROM = "captain-beefheart/p13f1"

READER_READY = """() => !document.body.classList.contains('loading') &&
  [...document.querySelectorAll('.slot:not([hidden]) img')].filter(i => i.getAttribute('src'))
    .every(i => i.complete && i.naturalWidth > 0)"""
SHELF_READY = """() => !document.body.classList.contains('loading') &&
  [...document.querySelectorAll('#books img')].every(i => i.complete && i.naturalWidth > 0)"""
INDEX_READY = """() => [...document.querySelectorAll('#index img')].filter(i => {
  const r = i.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; })
  .every(i => i.complete && i.naturalWidth > 0)"""
SHOW_CHROME = """() => { document.body.classList.remove('idle');
  document.getElementById('caption').classList.remove('tucked'); }"""


# ---------- capture ----------

class Capture:
    def __init__(self, browser, base, shots):
        self.browser, self.base, self.shots, self.errors = browser, base, shots, []

    def open(self, url, w, h, scale, mobile, ready):
        ctx = self.browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=scale,
                                       is_mobile=mobile, has_touch=mobile)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: self.errors.append(str(e)))
        pg.clock.install(time=T0)
        pg.goto(self.base + url)
        pg.wait_for_function(ready, timeout=30000)
        pg.clock.pause_at(T0 + dt.timedelta(minutes=5))
        pg.evaluate(SHOW_CHROME)
        time.sleep(0.8)  # CSS fades run in real time
        return ctx, pg

    def shot(self, pg, name):
        pg.screenshot(path=str(self.shots / f"{name}.png"))

    def hero(self):
        ctx, pg = self.open("#" + HERO_LAPTOP, 1440, 900, 2, False, READER_READY)
        self.shot(pg, "laptop-strip"); ctx.close()
        ctx, pg = self.open("#" + HERO_PHONE, 390, 844, 3, True, READER_READY)
        self.shot(pg, "phone-frame"); ctx.close()

    def phones(self):
        ctx, pg = self.open("", 390, 932, 3, True, SHELF_READY)
        self.shot(pg, "phone-shelf"); ctx.close()
        ctx, pg = self.open("#" + PHONES_INDEX, 390, 932, 3, True, READER_READY)
        pg.click("#open-index")
        pg.wait_for_function(INDEX_READY, timeout=30000)
        time.sleep(0.6)
        self.shot(pg, "phone-index"); ctx.close()
        ctx, pg = self.open("#" + PHONES_LAST, 390, 932, 3, True, READER_READY)
        pg.keyboard.press("ArrowRight")
        pg.wait_for_function("() => !document.getElementById('end').hidden")
        pg.wait_for_function("() => [...document.querySelectorAll('#end-books img')].every(i => i.complete && i.naturalWidth)")
        time.sleep(0.8)
        self.shot(pg, "phone-end"); ctx.close()

    def slide(self, moves=3, step_ms=30, steps=22):
        """Frames of three moves; returns [(file, hold)] where hold marks a resting frame."""
        ctx, pg = self.open("#" + SLIDE_FROM, 390, 844, 2, True, READER_READY)
        pg.wait_for_function("""() => [...document.querySelectorAll('.slot img')].filter(i => i.getAttribute('src'))
                                .every(i => i.complete && i.naturalWidth > 0)""", timeout=30000)
        time.sleep(0.5)
        frames = [("slide-000.png", True)]
        self.shot(pg, "slide-000")
        n = 1
        for _ in range(moves):
            pg.keyboard.press("ArrowRight")
            for k in range(steps):  # 660 ms covers the longest move
                pg.clock.run_for(step_ms)
                self.shot(pg, f"slide-{n:03d}")
                frames.append((f"slide-{n:03d}.png", k == steps - 1))
                n += 1
        ctx.close()
        return frames, step_ms


# ---------- framing ----------

def background(w, h):
    """Warm dark gradient that matches the site."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w / 2) / (w * 0.75)) ** 2 + ((y + h * 0.15) / (h * 1.05)) ** 2)
    t = np.clip(d, 0, 1)[..., None]
    inner, outer = np.array([52, 36, 26], np.float32), np.array([14, 11, 10], np.float32)
    return Image.fromarray((inner + (outer - inner) * (t ** 0.9)).astype(np.uint8), "RGB")


def round_mask(size, r):
    w, h = size
    m = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=r * SS, fill=255)
    return m.resize(size, Image.LANCZOS)


def drop_shadow(canvas, mask, xy, blur, off, k):
    sh = Image.new("L", canvas.size, 0)
    sh.paste(mask, (xy[0] + off[0], xy[1] + off[1]))
    canvas.paste((0, 0, 0), mask=sh.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * k)))


def device(screen, bezel, outer_r, inner_r):
    """A screenshot inside a rounded bezel. Returns (image, alpha mask)."""
    sw, sh = screen.size
    w, h = sw + 2 * bezel, sh + 2 * bezel
    body = Image.new("RGB", (w, h), (12, 12, 13))
    rim = round_mask((w, h), outer_r)
    rim.paste(0, (2, 2), round_mask((w - 4, h - 4), outer_r - 2))
    body.paste((58, 56, 54), mask=rim)
    body.paste(screen, (bezel, bezel), round_mask(screen.size, inner_r))
    return body, round_mask((w, h), outer_r)


def fit_h(im, h):
    return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)


def fit_w(im, w):
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def phone(im, height):
    screen = fit_h(im, height)
    bezel = round(height * 0.017)
    r = round(screen.width * 0.13)
    return device(screen, bezel, r + bezel, r)


def save_jpeg(im, path, width=1600):
    if im.width > width:
        im = fit_w(im, width)
    im.save(path, "JPEG", quality=86, optimize=True, progressive=True)
    print(f"  {path.name}: {im.width}x{im.height}, {path.stat().st_size // 1024} KB")


def compose_hero(shots, out):
    W, H = 2000, 1180
    canvas = background(W, H)
    lap, lap_mask = device(fit_w(Image.open(shots / "laptop-strip.png").convert("RGB"), 1560), 18, 30, 12)
    lx, ly = 90, 64
    base_w, base_h = lap.width + 150, 30
    bx, by = lx - 75, ly + lap.height - 2
    grad = np.linspace(0, 1, base_h)[:, None, None]
    top, bot = np.array([150, 147, 143]), np.array([72, 70, 68])
    base = Image.fromarray(np.broadcast_to(top + (bot - top) * grad, (base_h, base_w, 3)).astype(np.uint8))
    bmask = Image.new("L", (base_w * SS, base_h * SS), 0)
    ImageDraw.Draw(bmask).rounded_rectangle([0, -base_h * SS, base_w * SS - 1, base_h * SS - 1],
                                            radius=base_h * SS, fill=255)
    bmask = bmask.resize((base_w, base_h), Image.LANCZOS)
    notch = Image.new("L", (base_w, base_h), 0)
    ImageDraw.Draw(notch).rounded_rectangle([base_w // 2 - 90, -12, base_w // 2 + 90, 9], radius=9, fill=255)
    base.paste((96, 94, 91), mask=notch)
    drop_shadow(canvas, lap_mask, (lx, ly), 36, (0, 26), 0.75)
    drop_shadow(canvas, bmask, (bx, by), 18, (0, 14), 0.8)
    canvas.paste(lap, (lx, ly), lap_mask)
    canvas.paste(base, (bx, by), bmask)
    ph, ph_mask = phone(Image.open(shots / "phone-frame.png").convert("RGB"), 840)
    px, py = W - 90 - ph.width, H - 50 - ph.height
    drop_shadow(canvas, ph_mask, (px, py), 40, (-10, 30), 0.9)
    canvas.paste(ph, (px, py), ph_mask)
    save_jpeg(canvas, out / "hero.jpg")


def compose_phones(shots, out):
    items = [phone(Image.open(shots / f"{n}.png").convert("RGB"), 1000)
             for n in ("phone-shelf", "phone-index", "phone-end")]
    gap, px, py = 90, 110, 80
    canvas = background(sum(i[0].width for i in items) + gap * 2 + 2 * px, items[0][0].height + 2 * py)
    x = px
    for im, mask in items:
        drop_shadow(canvas, mask, (x, py), 34, (0, 26), 0.85)
        canvas.paste(im, (x, py), mask)
        x += im.width + gap
    save_jpeg(canvas, out / "phones.jpg")


def compose_slide(shots, out, frames, step_ms, width=280, every=2, colors=128, pad=18):
    kept, delays = [], []
    for i, (name, hold) in enumerate(frames):
        if not hold and i % every:
            continue
        im = Image.open(shots / name).convert("RGB")
        dev, mask = phone(im, round(im.height * width / im.width))
        bg = Image.new("RGB", (dev.width + 2 * pad, dev.height + 2 * pad), (22, 17, 14))
        bg.paste(dev, (pad, pad), mask)
        if kept and ImageChops.difference(bg, kept[-1]).getbbox() is None:
            delays[-1] = max(delays[-1] + step_ms * every, 1500 if hold else 0)
            continue
        kept.append(bg)
        delays.append(1500 if hold else step_ms * every)
    sample = Image.new("RGB", (kept[0].width, kept[0].height * 4))
    for k, i in enumerate(np.linspace(0, len(kept) - 1, 4).round().astype(int)):
        sample.paste(kept[i], (0, kept[0].height * k))
    pal = sample.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in kept]
    path = out / "slide.gif"
    q[0].save(path, save_all=True, append_images=q[1:], duration=delays, loop=0, optimize=True, disposal=1)
    print(f"  slide.gif: {q[0].width}x{q[0].height}, {len(q)} frames, {path.stat().st_size // 1024} KB")


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Rebuild the README images from the real reader.")
    ap.add_argument("which", nargs="*", help="hero, phones and/or slide (default: all three)")
    ap.add_argument("--out", default=str(ROOT / "screenshots"), help="folder to write to (default: screenshots/)")
    args = ap.parse_args()
    which = args.which or ["hero", "phones", "slide"]
    unknown = [w for w in which if w not in ("hero", "phones", "slide")]
    if unknown:
        ap.error(f"unknown image {', '.join(unknown)}: choose from hero, phones, slide")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("This needs Playwright: pip install playwright")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    shots = Path(tempfile.mkdtemp(prefix="mve-shots-"))
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome", headless=True)
            except Exception:
                browser = p.chromium.launch(headless=True)
            cap = Capture(browser, f"http://127.0.0.1:{srv.server_address[1]}/", shots)
            if "hero" in which:
                cap.hero()
            if "phones" in which:
                cap.phones()
            if "slide" in which:
                frames, step_ms = cap.slide()
            browser.close()
        if cap.errors:
            sys.exit("The reader logged errors, so no images were written: " + "; ".join(cap.errors))
        print(f"Writing to {out}")
        if "hero" in which:
            compose_hero(shots, out)
        if "phones" in which:
            compose_phones(shots, out)
        if "slide" in which:
            compose_slide(shots, out, frames, step_ms)
    finally:
        shutil.rmtree(shots, ignore_errors=True)
        srv.shutdown()


if __name__ == "__main__":
    main()
