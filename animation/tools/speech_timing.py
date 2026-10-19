#!/usr/bin/env python3
"""Ask Gemini who speaks when in each generated clip (and when the sound
effects happen), so speech bubbles can be timed to the lip movement.

    python animation/tools/speech_timing.py OUT.json CLIP.mp4 [CLIP.mp4 ...]

Needs GOOGLE_API_KEY. Clips over ~14 MB are skipped (inline request limit).
"""
import base64, json, os, pathlib, sys, urllib.request

KEY = os.environ["GOOGLE_API_KEY"]
PREFERRED = ["gemini-3.1-flash", "gemini-3-flash", "gemini-2.5-flash", "gemini-3-pro", "gemini-2.5-pro"]
PROMPT = (
    "This is a short animated comedy clip with painted ape characters. List every spoken "
    "utterance with its start and end time in seconds (one decimal), the speaker identified by "
    "costume (one of: 'red cape', 'cream coat', 'maroon jacket', 'steel helmet', 'plumber'), and "
    "the words spoken. Also list notable non-speech sounds (squeak, thud, hum, creak, laugh) with "
    "start and end times. Reply with JSON only: "
    '{"utterances":[{"start":0.0,"end":0.0,"speaker":"","text":""}],"sounds":[{"start":0.0,"end":0.0,"label":""}]}'
)

def models():
    d = json.load(urllib.request.urlopen(f"https://generativelanguage.googleapis.com/v1beta/models?key={KEY}&pageSize=200", timeout=60))
    return {m["name"].split("/")[-1] for m in d.get("models", [])}

def ask(model, path):
    data = base64.b64encode(pathlib.Path(path).read_bytes()).decode()
    body = {"contents": [{"parts": [{"text": PROMPT}, {"inline_data": {"mime_type": "video/mp4", "data": data}}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
    resp = json.load(urllib.request.urlopen(req, timeout=300))
    text = resp["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)

def main(out, clips):
    avail = models()
    model = next((m for m in PREFERRED if m in avail), None) or sorted(m for m in avail if "flash" in m and "image" not in m)[0]
    print("model:", model)
    result = {"model": model, "clips": {}}
    for c in clips:
        size = os.path.getsize(c)
        name = pathlib.Path(c).stem
        if size > 14_000_000:
            print(name, "skipped (too big)"); result["clips"][name] = {"skipped": "too big"}; continue
        try:
            r = ask(model, c); result["clips"][name] = r
            print(name, json.dumps(r)[:300])
        except Exception as e:
            print(name, "ERR", str(e)[:200]); result["clips"][name] = {"error": str(e)[:200]}
        pathlib.Path(out).write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("wrote", out)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
