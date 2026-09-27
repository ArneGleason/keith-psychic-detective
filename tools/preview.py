#!/usr/bin/env python3
"""Preview the comics site on this computer before pushing to GitHub.

Usage:  python3 tools/preview.py              open the site at http://localhost:8000/
        python3 tools/preview.py --phone      also let a phone on the same Wi-Fi open it
        python3 tools/preview.py --port 9000  use a particular port
        python3 tools/preview.py --no-open    don't open a browser window

It serves this working copy the way GitHub Pages will, with caching turned
off, so a rebuild shows up on the next reload. Stop it with Ctrl+C.
Needs only Python. Run tools/build.py first if you changed any comics.
"""
import argparse
import functools
import http.server
import json
import socket
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp"}


class Handler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        # GitHub Pages never serves hidden files such as .git, so neither do we.
        parts = unquote(urlsplit(self.path).path).split("/")
        if any(p.startswith(".") for p in parts if p):
            self.send_error(404)
            return None
        return super().send_head()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


def lan_address():
    """This computer's address on the local network, or None."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))   # picks a route; sends nothing
            ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None


def stale_builds():
    """Comics whose story file or images changed after their last build."""
    stale = []
    try:
        library = json.loads((ROOT / "tools" / "library.json").read_text())
        for cid in library["comics"]:
            built = ROOT / "comics" / cid / "comic.json"
            story = ROOT / "tools" / "stories" / f"{cid}.json"
            if not built.exists():
                stale.append(cid)
                continue
            built_at = built.stat().st_mtime
            source = ROOT / json.loads(story.read_text())["source"]
            inputs = [story, *(f for f in source.iterdir() if f.suffix.lower() in IMAGE_TYPES)]
            if any(f.stat().st_mtime > built_at for f in inputs):
                stale.append(cid)
    except (OSError, KeyError, ValueError):
        pass
    return stale


def pending_changes():
    """A short note on what is here but not on GitHub yet."""
    def git(*args):
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=10)
    try:
        ahead = git("rev-list", "--count", "@{u}..HEAD")
        dirty = git("status", "--porcelain")
    except (OSError, subprocess.SubprocessError):
        return None
    if ahead.returncode or dirty.returncode:
        return None
    n = int(ahead.stdout.strip() or 0)
    m = len([line for line in dirty.stdout.splitlines() if line.strip()])
    notes = []
    if n:
        notes.append(f"{n} commit{'s' if n != 1 else ''} not pushed")
    if m:
        notes.append(f"{m} uncommitted file{'s' if m != 1 else ''}")
    return ", ".join(notes) or "nothing new since the last push"


def bind(host, port, fixed):
    handler = functools.partial(Handler, directory=str(ROOT))
    for p in [port] if fixed else range(port, port + 20):
        try:
            return http.server.ThreadingHTTPServer((host, p), handler)
        except OSError:
            continue
    sys.exit(f"Port {port} is busy. Try another, for example --port {port + 100}.")


def main():
    ap = argparse.ArgumentParser(description="Preview the comics site before pushing.")
    ap.add_argument("--phone", action="store_true", help="let phones on the same Wi-Fi open it too")
    ap.add_argument("--port", type=int, help="port to use (default 8000, or the next free one)")
    ap.add_argument("--no-open", action="store_true", help="don't open a browser window")
    args = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)

    if not (ROOT / "comics" / "index.json").exists():
        sys.exit("There is nothing to preview yet. Run: python3 tools/build.py")

    server = bind("0.0.0.0" if args.phone else "127.0.0.1", args.port or 8000, args.port is not None)
    port = server.server_address[1]
    local = f"http://localhost:{port}/"

    print(f"Previewing {ROOT.name}")
    print(f"  On this computer:  {local}")
    if args.phone:
        ip = lan_address()
        if ip:
            print(f"  On your phone:     http://{ip}:{port}/   (same Wi-Fi as this computer)")
            print("  If macOS asks whether Python may accept incoming connections, choose Allow.")
        else:
            print("  On your phone:     no network found, so only this computer can open it")
    pending = pending_changes()
    if pending:
        print(f"  Not on GitHub yet: {pending}")
    for cid in stale_builds():
        print(f"  Heads up: {cid} changed since its last build. Run: python3 tools/build.py {cid}")
    print("Press Ctrl+C to stop.")

    if not args.no_open:
        threading.Timer(0.4, webbrowser.open, [local]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
