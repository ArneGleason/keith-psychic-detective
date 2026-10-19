#!/usr/bin/env python3
"""Generate an instrumental music cue with Google Lyria through the Gemini API.

    python animation/tools/lyria_music.py OUT_BASENAME "prompt" [--model lyria-3.5]

Needs GOOGLE_API_KEY. Writes OUT_BASENAME.<ext> (whatever audio type the model
returns) and OUT_BASENAME.json (model, prompt, mime type, any text parts).
"""
import base64
import json
import mimetypes
import os
import pathlib
import sys
import urllib.error
import urllib.request

EXT = {"audio/wav": ".wav", "audio/x-wav": ".wav", "audio/mpeg": ".mp3", "audio/mp3": ".mp3",
       "audio/ogg": ".ogg", "audio/flac": ".flac", "audio/L16": ".pcm"}


def main(argv):
    model = "lyria-3.5"
    if "--model" in argv:
        i = argv.index("--model")
        model = argv[i + 1]
        del argv[i:i + 2]
    base, prompt = pathlib.Path(argv[0]), argv[1]
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GOOGLE_API_KEY"]})
    try:
        resp = json.load(urllib.request.urlopen(req, timeout=600))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{model}: HTTP {e.code}: {e.read()[:600].decode(errors='replace')}")
    texts, n = [], 0
    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            if "inlineData" in part:
                mime = part["inlineData"]["mimeType"].split(";")[0]
                ext = EXT.get(mime) or mimetypes.guess_extension(mime) or ".bin"
                out = base.with_name(base.name + (f"_{n}" if n else "") + ext)
                out.write_bytes(base64.b64decode(part["inlineData"]["data"]))
                print("wrote", out, mime, part["inlineData"]["mimeType"])
                n += 1
            elif "text" in part:
                texts.append(part["text"])
    base.with_suffix(".json").write_text(json.dumps(
        {"model": model, "prompt": prompt, "texts": texts, "usage": resp.get("usageMetadata")}, indent=1), encoding="utf-8")
    if not n:
        raise SystemExit("no audio returned: " + json.dumps(resp)[:600])


if __name__ == "__main__":
    main(sys.argv[1:])
