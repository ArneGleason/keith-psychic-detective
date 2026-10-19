#!/usr/bin/env python3
"""Lay music and sound effects under a finished picture with ffmpeg.

    python animation/tools/mix_audio.py MIX.json OUT.mp4

MIX.json:
{
 "video": "../out/cut_silent.mp4",          (its own audio is ignored)
 "length": 48.8,
 "tracks": [
  {"src": "../audio/music.mp3", "in": 0.0, "out": 39.1, "at": 0.0, "gain_db": -2, "fade_in": 0, "fade_out": 0.15},
  {"src": "../audio/squeak.wav", "at": 39.3, "gain_db": 2}
 ]
}
"in"/"out" trim the source (seconds); "at" places it on the picture's
timeline. Paths are relative to the JSON. The picture is copied, not
re-encoded. Prints the integrated loudness and peak of the result.
"""
import json
import pathlib
import subprocess
import sys


def main(mix_path: str, out: str) -> None:
    mp = pathlib.Path(mix_path)
    mix = json.load(open(mp, encoding="utf-8"))
    base = mp.parent
    inputs = ["-i", str(base / mix["video"])]
    chains, labels = [], []
    for i, tr in enumerate(mix["tracks"], start=1):
        inputs += ["-i", str(base / tr["src"])]
        f = f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo"
        if "in" in tr or "out" in tr:
            f += f",atrim={tr.get('in', 0)}" + (f":{tr['out']}" if "out" in tr else "") + ",asetpts=PTS-STARTPTS"
        if tr.get("fade_in"):
            f += f",afade=t=in:st=0:d={tr['fade_in']}"
        if tr.get("fade_out"):
            length = tr["out"] - tr.get("in", 0)
            f += f",afade=t=out:st={length - tr['fade_out']}:d={tr['fade_out']}"
        if tr.get("gain_db"):
            f += f",volume={tr['gain_db']}dB"
        ms = int(round(tr.get("at", 0) * 1000))
        if ms:
            f += f",adelay={ms}|{ms}"
        chains.append(f + f"[t{i}]")
        labels.append(f"[t{i}]")
    graph = ";".join(chains) + ";" + "".join(labels) + \
        f"amix=inputs={len(labels)}:normalize=0:duration=longest,apad,atrim=0:{mix['length']}[a]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs + [
        "-filter_complex", graph, "-map", "0:v", "-map", "[a]", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    stats = subprocess.run(["ffmpeg", "-v", "info", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    summary = stats[stats.rfind("Summary:"):]
    lines = [l.strip() for l in summary.splitlines() if l.strip().startswith(("I:", "Peak:"))]
    print("wrote", out, "|", " ".join(lines))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
