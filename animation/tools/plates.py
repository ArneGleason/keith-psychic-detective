#!/usr/bin/env python3
"""Clean 16:9 keyframe plates for The Primate Suspects animation.

Regenerates comic panels without bubbles, lettering or borders, recomposed
for widescreen, using the panel crops (and the cover) as identity references.

    python animation/tools/plates.py animation/a-useful-man/plates PLATE_ID [PLATE_ID ...]
    python animation/tools/plates.py animation/a-useful-man/plates all

Needs OPENAI_API_KEY. Writes plates/out/<id>.png and plates/out/<id>.json.
"""
import base64
import json
import pathlib
import sys

from openai import OpenAI

MODEL = "gpt-image-2"
SIZE = "1536x1024"

# Identical on every plate. Change it here only, never per shot.
LOCK = (
    "THE PRIMATE SUSPECTS photo-comic look: a real 1970s practical ape mask and "
    "fur suit worn by an actor, tactile, slightly caricatured, readable "
    "expression, photographed like a 1960s American sitcom, warm tungsten "
    "light, tidy retro living room with floral wallpaper, polished side table, "
    "table lamp, framed wedding photo. "
    "MAJOR MALFUNCTION: short stocky brown ape, pale dented steel helmet with a "
    "small badge and chin strap, grey double-breasted military tunic with black "
    "collar and cuffs, brass buttons, yellow shoulder cords, yellow belt with "
    "round buckle, red neck scarf, grey trousers, black boots. "
    "LAURA PRITCHARD: adult human woman, dark flipped 1960s bob, fitted "
    "light-blue sweater, navy capri trousers, warm clever smile. "
    "THE CLOWN: a kitsch ceramic musical clown figurine with an accordion, red "
    "nose, polka-dot suit, on a round music-box base. "
    "Every hand has four fingers and a thumb. Widescreen 16:9 frame, eye level, "
    "35mm lens look, nothing cropped at the top of heads. "
    "ABSOLUTELY NO speech bubbles, NO lettering, NO captions, NO text of any "
    "kind, NO comic panel borders, NO paper texture, NO sound-effect words."
)

SRC = pathlib.Path("animation/a-useful-man/plates/src")
COVER = SRC / "cover_major.png"

PLATES = {
    # id: (reference images, action description)
    "P1_doorway_twoshot": (
        [SRC / "ep09_p2_honeymoon_present.png", SRC / "ep09_p1_borrow_your_muscles.png", COVER],
        "Medium two-shot. Laura stands beside the side table, one hand presenting "
        "the clown figurine that sits on the table, looking up at the Major with "
        "bright anticipation. The Major stands at her left, hands at his sides, "
        "attentive and eager. Both fully in frame from the waist up, the clown "
        "between them in the lower third."),
    "P2_major_holds_clown": (
        [SRC / "ep09_p3_delicate_things.png", SRC / "ep09_p2_honeymoon_present.png", COVER],
        "Medium shot. The Major holds the clown figurine carefully in both "
        "hands against his chest, looking down at it with great concentration. "
        "Laura beside him, hands clasped under her chin, watching the figurine a "
        "little too intently. The side table and lamp behind them."),
    "P3_aftermath": (
        [SRC / "ep09_p4_honeymoon_clown.png", SRC / "ep09_p3_delicate_things.png", COVER],
        "Medium shot. The clown figurine lies shattered on the coffee table, "
        "a spring and ceramic shards scattered, the accordion in two pieces. The "
        "Major stares at the pieces, appalled, mouth open, hands raised. Laura "
        "beside him with both hands over her mouth, eyes shining, barely hiding "
        "delight."),
    "P4_major_closeup": (
        [SRC / "ep09_p5_bear_up_somehow.png", COVER, SRC / "ep09_p3_delicate_things.png"],
        "Tight close-up: the Major's head, helmet and shoulders fill the frame, "
        "seated on the floral sofa, a teacup held just below the chin. Mouth "
        "closed, calm, slightly abashed, looking a little left of camera at "
        "someone off-frame. Eyes and mouth clearly visible under the helmet "
        "brim. Shallow depth of field. The clown figurine is NOT in this shot "
        "(it has already been broken); nothing on the side table but the lamp."),
    "P5_laura_closeup": (
        [SRC / "ep09_p5_bear_up_somehow.png", SRC / "ep09_p2_honeymoon_present.png"],
        "Tight close-up: Laura's head and shoulders fill the frame, seated on "
        "the floral sofa, turned a little toward camera right, a sweet carefully "
        "innocent smile, mouth closed, looking at someone just off-frame. "
        "Shallow depth of field, lamp glow behind. The clown figurine is NOT in "
        "this shot (it has already been broken)."),
}


def make(client: OpenAI, out: pathlib.Path, pid: str) -> None:
    refs, action = PLATES[pid]
    prompt = f"{action} {LOCK}"
    files = [open(p, "rb") for p in refs]
    try:
        result = client.images.edit(model=MODEL, image=files, prompt=prompt,
                                    size=SIZE, quality="high", n=1)
    finally:
        for f in files:
            f.close()
    img = base64.b64decode(result.data[0].b64_json)
    (out / f"{pid}.png").write_bytes(img)
    (out / f"{pid}.json").write_text(json.dumps({
        "id": pid, "model": MODEL, "size": SIZE, "refs": [p.name for p in refs],
        "prompt": prompt}, indent=1), encoding="utf-8")
    print("wrote", out / f"{pid}.png")


def main(argv: list[str]) -> None:
    root = pathlib.Path(argv[0])
    out = root / "out"
    out.mkdir(parents=True, exist_ok=True)
    ids = list(PLATES) if argv[1:] == ["all"] else argv[1:]
    client = OpenAI()
    for pid in ids:
        if (out / f"{pid}.png").exists():
            print("exists", pid)
            continue
        make(client, out, pid)


if __name__ == "__main__":
    main(sys.argv[1:])
