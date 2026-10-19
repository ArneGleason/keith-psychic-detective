#!/usr/bin/env python3
"""Make a balloon-free, widescreen plate from a published comic panel.

Edits the actual painted panel with a Gemini image model, so the comic's own
painterly look is the plate's look. Nothing is re-imagined: the prompt asks
for the same painting with the lettering removed and the scene extended to
16:9.

    python animation/tools/clean_panel.py IN.png OUT.png ["extra instruction"]
    python animation/tools/clean_panel.py IN.png OUT.png --model gemini-3.1-flash-image

Needs GOOGLE_API_KEY. Writes OUT.png and OUT.json (model, prompt).
"""
import base64
import json
import os
import pathlib
import sys
import urllib.request

DEFAULT_MODEL = "gemini-3-pro-image"
FALLBACK_MODEL = "gemini-3.1-flash-image"

PROMPT = (
    "This is one panel from a painted graphic novel. Produce the SAME painting "
    "as a clean widescreen 16:9 frame for animation: remove every speech "
    "balloon, caption box, sound-effect word and all lettering, and paint in "
    "what was behind them so nothing looks erased. Extend the scene naturally "
    "to the left and right to fill the wider frame, continuing the same room, "
    "furniture, light and brushwork. Keep every character exactly as painted: "
    "same faces, masks, fur, costumes, poses, expressions, props and colours. "
    "Keep the painterly, slightly caricatured illustration style with visible "
    "brushwork and rich colour; do not make it photographic, do not add halftone "
    "dots, do not add a border, do not add any text. "
)


def call(model: str, img_path: str, prompt: str) -> bytes:
    data = base64.b64encode(pathlib.Path(img_path).read_bytes()).decode()
    body = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/png", "data": data}},
        ]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": "16:9"},
        },
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GOOGLE_API_KEY"]},
    )
    resp = json.load(urllib.request.urlopen(req, timeout=300))
    for part in resp["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])
    raise RuntimeError("no image in response: " + json.dumps(resp)[:500])


def main(argv: list[str]) -> None:
    model = DEFAULT_MODEL
    if "--model" in argv:
        i = argv.index("--model")
        model = argv[i + 1]
        del argv[i:i + 2]
    src, dst = argv[0], argv[1]
    extra = argv[2] if len(argv) > 2 else ""
    prompt = PROMPT + extra
    try:
        img = call(model, src, prompt)
    except urllib.error.HTTPError as e:
        msg = e.read()[:300].decode(errors="replace")
        if model == DEFAULT_MODEL:
            print(f"{model} failed ({e.code}: {msg}); trying {FALLBACK_MODEL}")
            model = FALLBACK_MODEL
            img = call(model, src, prompt)
        else:
            raise SystemExit(f"{model} failed ({e.code}): {msg}")
    pathlib.Path(dst).write_bytes(img)
    pathlib.Path(dst).with_suffix(".json").write_text(
        json.dumps({"src": src, "model": model, "prompt": prompt}, indent=1), encoding="utf-8")
    print("wrote", dst, "with", model)


if __name__ == "__main__":
    main(sys.argv[1:])
