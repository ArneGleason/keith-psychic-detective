#!/usr/bin/env python3
"""Have Gemini listen to audio files and answer a question about them.

    python animation/tools/listen.py "question" FILE [FILE ...]

Each file is sent inline (keep them under ~14 MB). Needs GOOGLE_API_KEY.
Prints the model's answer.
"""
import base64
import json
import mimetypes
import os
import pathlib
import sys
import urllib.request

MODEL = os.environ.get("LISTEN_MODEL", "gemini-2.5-flash")


def main(question, files):
    parts = [{"text": question}]
    for f in files:
        mime = mimetypes.guess_type(f)[0] or "audio/wav"
        if mime == "audio/x-wav":
            mime = "audio/wav"
        parts.append({"text": f"File: {pathlib.Path(f).name}"})
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(pathlib.Path(f).read_bytes()).decode()}})
    body = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.2}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GOOGLE_API_KEY"]})
    resp = json.load(urllib.request.urlopen(req, timeout=300))
    print(resp["candidates"][0]["content"]["parts"][0]["text"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
