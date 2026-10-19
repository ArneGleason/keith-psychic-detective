#!/usr/bin/env python3
"""Assemble a paced cut from Kling clips and still cards with ffmpeg.

    python animation/tools/assemble_cut.py CUT.json OUT.mp4 [--mute]

CUT.json:
{
 "fps": 24, "size": [1920, 1080], "fade_cards": 0.3,
 "items": [
   {"card": "cards/title.png", "sec": 2.5},
   {"clip": "clips/S1.mp4", "trim": [0, 5.0], "hold_first": 1.5, "hold_last": 0.5},
   {"black": 0.5}
 ]
}

Clips keep their own audio (Kling's native sound) unless --mute; they are
scaled and padded to the output size. "hold_first" freezes the first frame
for that many seconds before the motion starts (silent), "hold_last" freezes
the last frame after it. Cards are silent stills with a short fade in and
out; "black" is a silent gap. Everything is concatenated in one ffmpeg run.
Paths are relative to the JSON's folder. The script also prints the start
time of every item, for lining up overlays.
"""
import json
import pathlib
import subprocess
import sys


def probe_duration(path: pathlib.Path) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", str(path)]).decode().strip()
    return float(out)


def main(cut_path: str, out_path: str, mute: bool = False) -> None:
    cut_file = pathlib.Path(cut_path)
    cut = json.load(open(cut_file, encoding="utf-8"))
    base = cut_file.parent
    fps = cut.get("fps", 24)
    w, h = cut.get("size", [1920, 1080])
    fade = cut.get("fade_cards", 0.3)
    inputs: list[str] = []
    filters: list[str] = []
    concat_in = ""
    n = 0
    t = 0.0
    timeline = []
    for it in cut["items"]:
        if "card" in it:
            d = it["sec"]
            inputs += ["-loop", "1", "-t", str(d), "-i", str(base / it["card"])]
            filters.append(
                f"[{n}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={fps},format=yuv420p,"
                f"fade=t=in:st=0:d={fade},fade=t=out:st={max(0, d - fade)}:d={fade},"
                f"setsar=1[v{n}];"
                f"anullsrc=r=48000:cl=stereo,atrim=0:{d},asetpts=PTS-STARTPTS[a{n}]")
            timeline.append((it["card"], t, d)); t += d
        elif "clip" in it:
            t0, t1 = it.get("trim", [0, None])
            head = it.get("hold_first", 0)
            tail = it.get("hold_last", 0)
            src = base / it["clip"]
            inputs += ["-i", str(src)]
            end = t1 if t1 is not None else probe_duration(src)
            d = head + (end - t0) + tail
            trim = f"trim=start={t0}:end={end},setpts=PTS-STARTPTS,"
            atrim = f"atrim=start={t0}:end={end},asetpts=PTS-STARTPTS"
            pad = ""
            if head:
                pad += f"tpad=start_mode=clone:start_duration={head},"
            if tail:
                pad += f"tpad=stop_mode=clone:stop_duration={tail},"
            audio = f"[{n}:a]{atrim},aresample=48000,aformat=channel_layouts=stereo"
            if head:
                audio += f",adelay={int(head * 1000)}|{int(head * 1000)}"
            if tail:
                audio += f",apad=pad_dur={tail}"
            if mute:
                audio = f"anullsrc=r=48000:cl=stereo,atrim=0:{d:.4f},asetpts=PTS-STARTPTS"
            filters.append(
                f"[{n}:v]{trim}{pad}scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={fps},format=yuv420p,setsar=1[v{n}];"
                f"{audio}[a{n}]")
            timeline.append((it["clip"], t, d)); t += d
        elif "black" in it:
            d = it["black"]
            inputs += ["-f", "lavfi", "-t", str(d), "-i", f"color=c=black:s={w}x{h}:r={fps}"]
            filters.append(
                f"[{n}:v]format=yuv420p,setsar=1[v{n}];"
                f"anullsrc=r=48000:cl=stereo,atrim=0:{d},asetpts=PTS-STARTPTS[a{n}]")
            timeline.append(("black", t, d)); t += d
        else:
            raise SystemExit(f"bad item: {it}")
        concat_in += f"[v{n}][a{n}]"
        n += 1
    graph = ";".join(filters) + f";{concat_in}concat=n={n}:v=1:a=1[v][a]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + inputs + [
        "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_path]
    subprocess.run(cmd, check=True)
    for name, start, d in timeline:
        print(f"{start:7.2f}  +{d:5.2f}  {name}")
    print("wrote", out_path, f"({t:.2f} s)")
    pathlib.Path(out_path).with_suffix(".timeline.json").write_text(
        json.dumps([{"item": a, "start": b, "sec": c} for a, b, c in timeline], indent=1), encoding="utf-8")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--mute"]
    main(args[0], args[1], mute="--mute" in sys.argv)
