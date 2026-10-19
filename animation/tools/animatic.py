#!/usr/bin/env python3
"""Animatic from the shot list: plates held for their durations, dialogue at
the shot starts, a title card at the end.

    python animation/tools/animatic.py animation/a-useful-man [--fit] [--out out/animatic_v1.mp4]

Reads <project>/shots/shotlist.json, <project>/plates/out/<plate>.png and
<project>/voices/lines/<shot>_<speaker>.wav. With --fit, any dialogue shot
shorter than line offset + line length + line_gap_sec is extended and the new
timings are written back to the shot list (it stays the source of truth).
Each frame carries a small review label (shot id, plate, speaker, SFX).
Needs ffmpeg and Pillow.
"""
import array
import json
import pathlib
import struct
import subprocess
import sys
import wave

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FONT_BOLD = "C:/Windows/Fonts/impact.ttf"
FONT_LABEL = "C:/Windows/Fonts/bahnschrift.ttf"
TEAL, YELLOW, RED = (31, 92, 104), (250, 214, 52), (200, 40, 40)


def wav_data(path: pathlib.Path) -> tuple[int, int, int, bytes]:
    """(rate, channels, sample width, pcm bytes). Streamed TTS WAVs carry a bogus frame
    count in the header, so the data chunk is measured, not trusted."""
    raw = path.read_bytes()
    fmt = raw.index(b"fmt ", 12) + 8
    ch, rate = struct.unpack_from("<HI", raw, fmt + 2)
    width = struct.unpack_from("<H", raw, fmt + 14)[0] // 8
    return rate, ch, width, raw[raw.index(b"data", 12) + 8:]


def wav_seconds(path: pathlib.Path) -> float:
    rate, ch, width, pcm = wav_data(path)
    return len(pcm) / (ch * width) / rate


def fit(doc: dict, lines: dict) -> list[str]:
    """Extend dialogue shots so the line and the gap fit. Returns a change log."""
    gap, lead = doc["line_gap_sec"], doc["line_lead_sec"]
    changed, t = [], 0.0
    for s in doc["shots"]:
        if s["id"] in lines:
            need = s.get("line_offset_sec", lead) + wav_seconds(lines[s["id"]]) + gap
            need = round(-(-need * 10 // 1) / 10, 1)  # ceil to 0.1 s
            if need > s["dur_sec"]:
                changed.append(f"{s['id']} {s['dur_sec']:.1f} -> {need:.1f} s")
                s["dur_sec"] = need
        s["start_sec"] = round(t, 3)
        s["end_sec"] = round(t + s["dur_sec"], 3)
        s["frames"] = round(s["dur_sec"] * doc["fps"])
        t += s["dur_sec"]
    doc["duration_sec"] = round(t, 3)
    return changed


def frame_from_plate(plate: pathlib.Path, label: str, dst: pathlib.Path) -> None:
    img = Image.open(plate).convert("RGB")
    w, h = img.size
    if abs(w / h - 1.5) > 0.05:  # a page panel standing in for a 3:2 plate: fit, never crop
        return frame_from_panel(plate, label, dst)
    th = round(w * 9 / 16)
    if th < h:  # crop a 3:2 plate to 16:9, keeping a little more headroom than footroom
        top = max(0, round((h - th) * 0.4))
        img = img.crop((0, top, w, top + th))
    img = img.resize((W, H), Image.LANCZOS)
    stamp(img, label)
    img.save(dst)


def stamp(img: Image.Image, label: str) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    f = ImageFont.truetype(FONT_LABEL, 30)
    tw = d.textlength(label, font=f)
    d.rectangle((24, H - 70, 24 + tw + 24, H - 24), fill=(0, 0, 0, 150))
    d.text((36, H - 64), label, font=f, fill=(255, 255, 255, 230))


def find_plate(project: pathlib.Path, s: dict):
    """The approved plate, else a rejected version, else the source panel crop, else None.
    Returns (path or None, status label or '')."""
    out = project / "plates" / "out"
    plate = out / f"{s['plate']}.png"
    if plate.exists():
        return plate, ""
    older = sorted(out.glob(f"{s['plate']}_v*.png"))
    if older:
        return older[-1], f"REGEN PENDING ({older[-1].stem.split('_v', 1)[1]})"
    src = s.get("source", "").replace(" ", "_")  # "ep14 p4" -> ep14_p4_*.png
    panels = sorted((project / "plates" / "src").glob(f"{src}_*.png")) if src else []
    if panels:
        return panels[0], "PLATE PENDING (panel stand-in)"
    return None, "PLATE PENDING"


def frame_from_panel(panel: pathlib.Path, label: str, dst: pathlib.Path) -> None:
    img = Image.open(panel).convert("RGB")
    scale = min(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    card = Image.new("RGB", (W, H), (28, 28, 28))
    card.paste(img, ((W - img.width) // 2, (H - img.height) // 2))
    stamp(card, label)
    card.save(dst)


def text_card(dst: pathlib.Path, head: str, body: str, label: str) -> None:
    img = Image.new("RGB", (W, H), (28, 28, 28))
    d = ImageDraw.Draw(img)
    d.text((120, 260), head, font=ImageFont.truetype(FONT_BOLD, 90), fill=(250, 214, 52))
    f = ImageFont.truetype(FONT_LABEL, 44)
    words, lines, cur = body.split(), [], ""
    for w_ in words:
        if d.textlength(cur + " " + w_, font=f) > W - 240:
            lines.append(cur)
            cur = w_
        else:
            cur = (cur + " " + w_).strip()
    lines.append(cur)
    d.multiline_text((120, 420), "\n".join(lines), font=f, fill=(230, 230, 230), spacing=14)
    stamp(img, label)
    img.save(dst)


def title_card(dst: pathlib.Path, title: str, sub: str) -> None:
    img = Image.new("RGB", (W, H), TEAL)
    d = ImageDraw.Draw(img)
    f1, f2 = ImageFont.truetype(FONT_BOLD, 190), ImageFont.truetype(FONT_BOLD, 70)
    for text, font, y, fill in ((title, f1, 330, YELLOW), (sub.upper(), f2, 640, (255, 255, 255))):
        tw = d.textlength(text, font=font)
        x = (W - tw) / 2
        if fill is YELLOW:
            d.text((x + 10, y + 10), text, font=font, fill=RED)
        d.text((x, y), text, font=font, fill=fill)
    img.save(dst)


def audio_bed(doc: dict, lines: dict, dst: pathlib.Path) -> None:
    rate = 24000
    total = int(doc["duration_sec"] * rate) + rate
    mix = array.array("h", bytes(2 * total))
    for s in doc["shots"]:
        if s["id"] not in lines:
            continue
        fmt = wav_data(lines[s["id"]])
        assert fmt[:3] == (rate, 1, 2), (lines[s["id"]], fmt[:3])
        data = array.array("h", fmt[3][: len(fmt[3]) // 2 * 2])
        at = int((s["start_sec"] + s.get("line_offset_sec", doc["line_lead_sec"])) * rate)
        for i, v in enumerate(data):
            j = at + i
            if j < total:
                mix[j] = max(-32768, min(32767, mix[j] + v))
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(mix.tobytes())


def main(argv: list[str]) -> None:
    project = pathlib.Path(argv[0])
    do_fit = "--fit" in argv
    out_rel = argv[argv.index("--out") + 1] if "--out" in argv else "out/animatic_v1.mp4"
    shotlist = project / "shots" / "shotlist.json"
    doc = json.loads(shotlist.read_text(encoding="utf-8"))
    lines = {s["id"]: project / "voices" / "lines" / f"{s['id']}_{s['speaker']}.wav"
             for s in doc["shots"] if s.get("line")}
    missing = [str(p) for p in lines.values() if not p.exists()]
    if missing:
        sys.exit("missing lines: " + ", ".join(missing))
    if do_fit:
        for c in fit(doc, lines):
            print("fit", c)
        shotlist.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    out = project / out_rel
    work = out.parent / "_animatic"
    work.mkdir(parents=True, exist_ok=True)
    concat, pending = [], []
    for s in doc["shots"]:
        frame = work / f"{s['id']}.png"
        if s["plate"] == "TITLE":
            title_card(frame, doc["series"].upper(), doc["title"])
        else:
            bits = [s["id"], s["plate"]]
            if s.get("speaker"):
                bits.append(s["speaker"].upper())
            bits += [x for x in s.get("sfx", []) if x.isupper() or "lettering" in x]
            plate, status = find_plate(project, s)
            if status:
                bits.append(status)
                pending.append(f"{s['id']} {s['plate']}: {status}")
            if plate is None:
                text_card(frame, f"{s['id']}  PLATE PENDING", s["action"], "  ·  ".join(bits))
            else:
                frame_from_plate(plate, "  ·  ".join(bits), frame)
        concat += [f"file '{frame.name}'", f"duration {s['dur_sec']}"]
    concat.append(f"file '{frame.name}'")  # concat demuxer needs the last file repeated
    (work / "list.txt").write_text("\n".join(concat) + "\n", encoding="utf-8")
    audio_bed(doc, lines, work / "dialogue.wav")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
        "-i", str(work / "list.txt"), "-i", str(work / "dialogue.wav"),
        "-vf", f"fps={doc['fps']},format=yuv420p", "-c:v", "libx264", "-crf", "20",
        "-preset", "medium", "-c:a", "aac", "-b:a", "128k", "-shortest",
        "-movflags", "+faststart", str(out)], check=True)
    for line in pending:
        print("placeholder", line)
    print(f"wrote {out} ({doc['duration_sec']:.1f} s, {len(doc['shots'])} shots, "
          f"{len(pending)} placeholders)")


if __name__ == "__main__":
    main(sys.argv[1:])
