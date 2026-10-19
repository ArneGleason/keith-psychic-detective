#!/usr/bin/env python3
"""Generate dialogue lines with the placeholder cast.

    python animation/tools/lines.py animation/a-useful-man/voices/casting/casting.json \
        animation/a-useful-man/shots/lines.json animation/a-useful-man/voices/lines

lines.json: [{"id": "T3a", "speaker": "laura", "text": "..."}, ...]
Each line is rendered with the speaker's voice and instruction from the
casting manifest, so every line of a character sounds like the same actor.
"""
import json
import pathlib
import sys

from openai import OpenAI


def main(casting_path: str, lines_path: str, out_dir: str) -> None:
    cast = {m["name"]: m for m in json.load(open(casting_path, encoding="utf-8"))}
    lines = json.load(open(lines_path, encoding="utf-8"))
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    client = OpenAI()
    for ln in lines:
        wav = out / f"{ln['id']}_{ln['speaker']}.wav"
        if wav.exists():
            print("exists", wav.name)
            continue
        m = cast[ln["speaker"]]
        with client.audio.speech.with_streaming_response.create(
            model=m["model"], voice=m["voice"], input=ln["text"],
            instructions=m["instructions"], response_format="wav",
        ) as resp:
            resp.stream_to_file(wav)
        print("wrote", wav.name)


if __name__ == "__main__":
    main(*sys.argv[1:4])
