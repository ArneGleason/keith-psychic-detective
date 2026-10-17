#!/usr/bin/env python3
"""Read through a comic in a headless browser, the way a visitor would.

It opens the comic on a phone and on a laptop, presses the right arrow until
the end page appears, and reports every stop. It then checks the shelf and
that the other comics still open, and lists any errors the page logged.

Usage:  python3 tools/check_reader.py primate-suspects          this copy, before pushing
        python3 tools/check_reader.py primate-suspects --live   the published site
        python3 tools/check_reader.py tom-waits --shot tom-waits/p15f2 --out /tmp/shots

--shot saves a screenshot when the walk reaches that stop (repeatable).
--quiet prints only the summary lines.

Needs:  pip install playwright   It uses your installed Google Chrome. Without
        Chrome, also run "python3 -m playwright install chromium" once.
"""
import argparse
import functools
import http.server
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE = "https://arnegleason.github.io/keith-psychic-detective/"

READY = """() => !document.body.classList.contains('loading') &&
  [...document.querySelectorAll('.slot:not([hidden]) img')].filter(i => i.getAttribute('src'))
    .every(i => i.complete && i.naturalWidth > 0)"""
STATE = """() => {
  const strip = document.getElementById('mode-strip');
  const [at, of] = document.getElementById('cap-count').textContent.split('/').map(Number);
  return { hash: location.hash,
           mode: strip.getAttribute('aria-pressed') === 'true' ? strip.textContent : 'Frame',
           scene: document.getElementById('cap-scene').textContent,
           frame: document.getElementById('cap-frame').textContent,
           at, of, end: !document.getElementById('end').hidden,
           endText: document.getElementById('end-kicker').textContent };
}"""
SHOW_CHROME = """() => { document.body.classList.remove('idle');
  document.getElementById('caption').classList.remove('tucked'); }"""
SIZES = (("phone", 390, 844, True), ("laptop", 1440, 900, False))


def serve_local():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}/"


def launch(p):
    try:
        return p.chromium.launch(channel="chrome", headless=True)
    except Exception:
        return p.chromium.launch(headless=True)


def walk(browser, base, comic, label, w, h, mobile, shots, out, quiet, errors):
    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2,
                              is_mobile=mobile, has_touch=mobile)
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(f"{label}: {e}"))
    pg.on("console", lambda m: m.type == "error" and errors.append(f"{label}: {m.text}"))
    pg.goto(base + "#" + comic)
    pg.wait_for_function(READY, timeout=30000)
    time.sleep(0.6)
    seq = [pg.evaluate(STATE)]
    for _ in range(seq[0]["of"] + 2):
        pg.keyboard.press("ArrowRight")
        time.sleep(0.7)
        s = pg.evaluate(STATE)
        seq.append(s)
        if s["end"]:
            break
        if s["hash"].lstrip("#") in shots:
            pg.evaluate(SHOW_CHROME)
            time.sleep(0.3)
            path = out / f"{label}-{s['hash'].lstrip('#').replace('/', '-')}.png"
            pg.screenshot(path=str(path))
            print(f"  saved {path}")
    loaded = pg.evaluate("""[...document.querySelectorAll('.slot img')].filter(i => i.getAttribute('src'))
                            .map(i => i.complete && i.naturalWidth > 0)""")
    ctx.close()

    stops = [s for s in seq if not s["end"]]
    in_order = [s["at"] for s in stops] == list(range(1, len(stops) + 1)) and stops[-1]["at"] == stops[-1]["of"]
    ok = in_order and seq[-1]["end"] and all(loaded)
    print(f"{label}: {stops[0]['mode']} mode, {len(stops)} stops, "
          f"{'in order' if in_order else 'OUT OF ORDER'}, "
          f"end page: {seq[-1]['endText'] if seq[-1]['end'] else 'NEVER REACHED'}, "
          f"images loaded {sum(loaded)}/{len(loaded)}")
    if not quiet:
        for s in stops:
            print(f"    {s['at']:>3}/{s['of']}  {s['hash']:<26} {s['scene']}  {s['frame']}")
    return ok


def main():
    ap = argparse.ArgumentParser(description="Read through a comic in a headless browser.")
    ap.add_argument("comic", help="comic id, as in tools/library.json")
    ap.add_argument("--live", action="store_true", help="check the published site instead of this copy")
    ap.add_argument("--shot", action="append", default=[], metavar="COMIC/pNfN", help="screenshot this stop")
    ap.add_argument("--out", default=".", help="folder for screenshots (default: current folder)")
    ap.add_argument("--quiet", action="store_true", help="print only summary lines")
    args = ap.parse_args()

    ids = json.loads((ROOT / "tools" / "library.json").read_text())["comics"]
    if args.comic not in ids:
        sys.exit(f"Unknown comic {args.comic!r}. Known: {', '.join(ids)}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("This needs Playwright: pip install playwright")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base = LIVE if args.live else serve_local()
    print(f"Checking {args.comic} on {'the live site' if args.live else 'this copy'}")

    errors, ok = [], True
    with sync_playwright() as p:
        browser = launch(p)
        for label, w, h, mobile in SIZES:
            ok &= walk(browser, base, args.comic, label, w, h, mobile, set(args.shot), out, args.quiet, errors)

        pg = browser.new_page(viewport={"width": 1440, "height": 900})
        pg.on("pageerror", lambda e: errors.append(f"shelf: {e}"))
        pg.goto(base)
        pg.wait_for_function("() => !document.body.classList.contains('loading')")
        shelf = pg.evaluate("""[...document.querySelectorAll('#books .book')].map(a =>
            a.querySelector('.book-title').textContent + ': ' + a.querySelector('.book-meta').textContent)""")
        print("shelf: " + " | ".join(shelf))
        for other in (c for c in ids if c != args.comic):
            pg.goto(base + "#" + other + "/p2")
            pg.wait_for_function(READY, timeout=30000)
            s = pg.evaluate(STATE)
            print(f"other comic opens: {other}, {s['mode']} mode, {s['scene']}")
        browser.close()

    print("errors: " + ("; ".join(errors) if errors else "none"))
    sys.exit(0 if ok and not errors else 1)


if __name__ == "__main__":
    main()
