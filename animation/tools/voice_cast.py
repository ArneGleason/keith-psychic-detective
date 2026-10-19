#!/usr/bin/env python3
"""Placeholder voice casting for The Primate Suspects.

Generates one line per character with OpenAI gpt-4o-mini-tts (fixed voice +
fixed instruction = consistent casting), then an audition reel.

    python animation/tools/voice_cast.py animation/a-useful-man/voices/casting

Needs OPENAI_API_KEY and ffmpeg. Lines are taken from the published pages.
"""
import json
import pathlib
import subprocess
import sys

from openai import OpenAI

MODEL = "gpt-4o-mini-tts"

# name, voice, instruction, line. Telepathy sources get a "head" treatment in the reel.
CAST = [
    ("major", "ash",
     "Warm, eager, earnest, a slight military clip. British. Delighted to be asked for help. Never sarcastic.",
     "Oh. Certainly. I'm not very good with delicate things. Fortunately, I'm not a man."),
    ("major_alt", "verse",
     "Warm, eager, earnest, a slight military clip. British. Delighted to be asked for help. Never sarcastic.",
     "Oh. Certainly. I'm not very good with delicate things. Fortunately, I'm not a man."),
    ("professor", "fable",
     "Pompous British academic. Self-satisfied pedantic precision, savouring the long words, utterly certain.",
     "I think you'll find a crouton is merely a structurally compromised toast. Right again. Eventually."),
    ("count", "onyx",
     "Dry, tired, dignified, faintly theatrical. British. Low energy, perfectly timed.",
     "Every bloody time. Eight hours. You missed it."),
    ("boggler", "echo",
     "Tentative, courteous, confused by his own thoughts. British. Sincere, slightly alarmed.",
     "Banana. I'm thinking about a banana. Who said that? Professor! I can read another mind!"),
    ("laura", "shimmer",
     "Sweet, bright, carefully innocent 1960s American sitcom wife. Warm and clever, hiding a plan.",
     "My husband gave me this on our honeymoon. It really deserves a more prominent position. Just over the fireplace, dear."),
    ("laura_alt", "coral",
     "Sweet, bright, carefully innocent 1960s American sitcom wife. Warm and clever, hiding a plan.",
     "My husband gave me this on our honeymoon. It really deserves a more prominent position. Just over the fireplace, dear."),
    ("rob", "alloy",
     "Breezy, lanky, conspiratorial American husband, 1960s sitcom. Cheerful and a little too casual.",
     "Could you look at this fan? It's stopped turning. Oh, I'm sure it'll be fine."),
    ("agatha", "sage",
     "Clipped, authoritative, elderly British academic. Restrained, unimpressed by her son.",
     "And when do you start talking to people?"),
    ("goat", "ballad",
     "Gruff, flat, bored, unimpressed. A goat's inner voice. Deadpan, no energy.",
     "I like her singing. It keeps the foxes away. Don't fucking rush me."),
    ("clive", "verse",
     "Blunt, gravelly, foul-mouthed ceramic garden gnome. Northern English, world-weary.",
     "Plenty of lonely bastards round here. Not a fucking clue between them."),
]
TELEPATHY = {"goat", "clive"}


def main(out_dir: str) -> None:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    client = OpenAI()
    manifest = []
    for name, voice, instruction, line in CAST:
        wav = out / f"{name}.wav"
        if not wav.exists():
            with client.audio.speech.with_streaming_response.create(
                model=MODEL, voice=voice, input=line,
                instructions=instruction, response_format="wav",
            ) as resp:
                resp.stream_to_file(wav)
        if name in TELEPATHY:
            treated = out / f"{name}_head.wav"
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                "-af", "lowpass=f=3200,highpass=f=180,acompressor=threshold=-18dB:ratio=3,volume=0.9",
                str(treated)], check=True)
            wav = treated
        manifest.append({"name": name, "voice": voice, "model": MODEL,
                         "instructions": instruction, "line": line, "file": wav.name})
        print(f"{name:12s} {voice:8s} -> {wav.name}")
    (out / "casting.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    # Audition reel: 0.7 s gap between lines, in cast order.
    gap = out / "_gap.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=24000:cl=mono", "-t", "0.7", str(gap)], check=True)
    lst = out / "_reel.txt"
    lines = []
    for m in manifest:
        lines.append(f"file '{m['file']}'")
        lines.append(f"file '{gap.name}'")
    lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-ar", "24000", "-ac", "1", str(out / "casting_reel.wav")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / "casting_reel.wav"),
                    "-b:a", "128k", str(out / "casting_reel.mp3")], check=True)
    print("reel:", out / "casting_reel.mp3")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "animation/a-useful-man/voices/casting")
