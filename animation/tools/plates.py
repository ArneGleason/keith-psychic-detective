#!/usr/bin/env python3
"""Clean 16:9 keyframe plates for The Primate Suspects animation.

Regenerates comic panels without bubbles, lettering or borders, recomposed
for widescreen, using the panel crops (and the cover) as identity references.

    python animation/tools/plates.py animation/a-useful-man/plates PLATE_ID [PLATE_ID ...]
    python animation/tools/plates.py animation/a-useful-man/plates all

Needs OPENAI_API_KEY. Writes plates/out/<id>.png and plates/out/<id>.json
(the exact prompt and references used). Existing PNGs are skipped: to
regenerate a plate, rename or delete its PNG first. Up to JOBS plates render
at once.

LOCK history: v1 (test battery, P1-P5, 2026-10-19 morning) described only the
Major, Laura and the clown. v2 (the film, same day) adds the Count, Rob, the
sets and every prop, and says that unnamed characters and props stay out of
frame. Each plate's .json records the prompt it was actually made with.
"""
import base64
import concurrent.futures
import json
import pathlib
import sys

from openai import OpenAI

MODEL = "gpt-image-2"
SIZE = "1536x1024"
JOBS = 3

# Identical on every plate. Change it here only, never per shot.
LOCK = (
    "THE PRIMATE SUSPECTS photo-comic look: real 1970s practical ape masks and "
    "fur suits worn by actors, tactile, slightly caricatured, readable "
    "expressions, photographed like a 1960s American sitcom, warm tungsten "
    "light, 35mm lens look. "
    "SETS. The Pritchards' tidy retro living room: floral wallpaper, floral "
    "sofa, polished wooden side table with a table lamp, framed wedding photo, "
    "low coffee table, a fireplace with a mantel; on its far wall a brown "
    "wooden home organ with two keyboards and a bench, a sheet-music book on "
    "its stand, and above the organ a wooden wall shelf. The apes' "
    "headquarters kitchen: shabby and cluttered, faded floral wallpaper, an "
    "old round-shouldered fridge, a gas stove, a tiled counter, a chrome "
    "toaster, a bowl of bananas. "
    "MAJOR MALFUNCTION: short stocky brown ape, pale dented steel helmet with a "
    "small badge and chin strap, grey double-breasted military tunic with black "
    "collar and cuffs, brass buttons, yellow shoulder cords, yellow belt with "
    "round buckle, red neck scarf, grey trousers, black boots. "
    "COUNT NAPULA: brown ape with short auburn hair, navy double-breasted coat, "
    "red cape and red scarf, dry, tired, dignified. "
    "LAURA PRITCHARD: adult human woman, dark flipped 1960s bob, fitted "
    "light-blue sweater, navy capri trousers, warm clever smile. "
    "ROB PRITCHARD: adult human man, lanky, dark neatly side-parted hair, big "
    "easy toothy grin, tan cardigan over a white shirt and narrow black tie, "
    "dark trousers. "
    "PROPS. THE CLOWN: a kitsch ceramic musical clown figurine with an "
    "accordion, red nose, polka-dot suit, on a round music-box base. "
    "THE FIGURINE: a kitsch porcelain ballerina in a pink tutu on a gilt base. "
    "THE FLYER: a printed paper flyer showing a green pool table, headline "
    "POOL TABLE SALE. THE FAN: a 1950s chrome desk fan with a round wire cage. "
    "THE TROPHY: a tall gold bowling trophy with a bowler figure on top. "
    "THE BALL: a glossy black bowling ball. THE BOBBLEHEAD: a small "
    "chimney-sweep bobblehead in a black top hat and sooty coat holding a tiny "
    "brush. THE SIGN: a hand-lettered card on the headquarters fridge reading "
    "DAYS WITHOUT POOP FLING: 1. "
    "Only the people and props the shot names are in frame; any character or "
    "prop the shot does not name is absent. Every hand has four fingers and a "
    "thumb. Widescreen 16:9 frame, eye level unless the shot says otherwise, "
    "nothing cropped at the top of heads. "
    "ABSOLUTELY NO speech bubbles, NO lettering, NO captions, NO comic panel "
    "borders, NO paper texture, NO sound-effect words, and no text of any kind "
    "except the print on a prop the shot names."
)

SRC = pathlib.Path("animation/a-useful-man/plates/src")
COVER = SRC / "cover_major.png"


def ep(n: str) -> pathlib.Path:
    return SRC / f"{n}.png"


# Close-ups for Kling Avatar: one face, mouth closed, eyes to someone off-frame.
CU = ("Mouth closed, looking a little {side} of camera at someone off-frame. "
      "Shallow depth of field. Nobody else in frame.")
# Episode 14 is after the clown broke; the LOCK's prop list alone did not keep it out.
EP14 = ("THE CLOWN and THE FIGURINE are NOT in this shot: no figurines or ornaments on "
        "any table. ")

PLATES = {
    # id: (reference images, shot description)
    # --- test battery (made with LOCK v1; kept as the record) ---
    "P1_doorway_twoshot": (
        [ep("ep09_p2_honeymoon_present"), ep("ep09_p1_borrow_your_muscles"), COVER],
        "Pritchard living room. Medium two-shot. Laura stands beside the side table, one hand "
        "presenting THE CLOWN that sits on the table, looking up at the Major with bright "
        "anticipation. The Major stands at her left, hands at his sides, attentive and eager. Both "
        "fully in frame from the waist up, the clown between them in the lower third."),
    "P2_major_holds_clown": (
        [ep("ep09_p3_delicate_things"), ep("ep09_p2_honeymoon_present"), COVER],
        "Pritchard living room. Medium shot. The Major holds THE CLOWN carefully in both hands "
        "against his chest, looking down at it with great concentration. Laura beside him, hands "
        "clasped under her chin, watching the figurine a little too intently. The side table and "
        "lamp behind them."),
    "P3_aftermath": (
        [ep("ep09_p4_honeymoon_clown"), ep("ep09_p3_delicate_things"), COVER],
        "Pritchard living room. Medium shot. THE CLOWN lies shattered on the coffee table, a spring "
        "and ceramic shards scattered, the accordion in two pieces. The Major stares at the pieces, "
        "appalled, mouth open, hands raised. Laura beside him with both hands over her mouth, eyes "
        "shining, barely hiding delight."),
    "P4_major_closeup": (
        [ep("ep09_p5_bear_up_somehow"), COVER, ep("ep09_p3_delicate_things")],
        "Pritchard living room. Tight close-up: the Major's head, helmet and shoulders fill the "
        "frame, seated on the floral sofa, a teacup held just below the chin. Mouth closed, calm, "
        "slightly abashed, looking a little left of camera at someone off-frame. Eyes and mouth "
        "clearly visible under the helmet brim. Shallow depth of field. THE CLOWN is NOT in this "
        "shot (it has already been broken); nothing on the side table but the lamp."),
    "P5_laura_closeup": (
        [ep("ep09_p5_bear_up_somehow"), ep("ep09_p2_honeymoon_present")],
        "Pritchard living room. Tight close-up: Laura's head and shoulders fill the frame, seated "
        "on the floral sofa, turned a little toward camera right, a sweet carefully innocent smile, "
        "mouth closed, looking at someone just off-frame. Shallow depth of field, lamp glow behind. "
        "THE CLOWN is NOT in this shot (it has already been broken)."),
    # --- cold open (episode 1) ---
    "P6_hq_kitchen_wide": (
        [ep("ep01_p1_morning_major"), ep("ep01_p2_every_bloody_time"), COVER],
        "Headquarters kitchen. Wide two-shot at the counter. The Count stands at the gas stove on "
        "the left wearing a floral apron over his navy coat and red cape, turning two fried eggs in "
        "a frying pan with a spatula, his face turned to the pan. The Major stands at the counter "
        "on the right dropping two slices of white bread into the chrome toaster, bright and eager. "
        "On the fridge behind the Count hangs THE SIGN under a magnet. The bowl of bananas on the "
        "counter. Both apes in frame from the waist up."),
    "P7_major_toaster_mcu": (
        [ep("ep01_p1_morning_major"), COVER, ep("ep01_p3_fixed_the_toilet")],
        "Headquarters kitchen. Medium close-up of the Major alone, head, helmet and shoulders "
        "filling the left two thirds of the frame, one hand resting on the lever of the chrome "
        "toaster in the lower right, bread in the slots, not yet pushed down. Bright and eager. "
        "Eyes and mouth clearly visible under the helmet brim. " + CU.format(side="left")),
    "P8_toaster_pfft_insert": (
        [ep("ep01_p2_every_bloody_time"), ep("ep01_p3_fixed_the_toilet")],
        "Headquarters kitchen. Close insert on the chrome toaster on the tiled counter: the Major's "
        "furry hand presses the lever down, his grey tunic cuff with black trim and a brass button "
        "in frame, no face. The toaster has just begun to spark, a few sparks and a thin wisp of "
        "smoke rising from the slots. Nothing else in frame but the counter, a banana and the "
        "kitchen wall."),
    "P9_count_mcu": (
        [ep("ep01_p2_every_bloody_time"), ep("ep01_p1_morning_major"), ep("ep01_p3_fixed_the_toilet")],
        "Headquarters kitchen. Medium close-up of the Count alone, head and shoulders filling the "
        "frame, floral apron straps over the navy coat and red cape, a spatula held up in one hand, "
        "a drift of grey toaster smoke passing in front of him. Tired, dead-eyed. "
        + CU.format(side="right")),
    # --- episode 9: arrival ---
    "P10_ext_house_day": (
        [ep("ep09_p1_borrow_your_muscles"), COVER],
        "Exterior, daytime. A tidy white 1960s American suburban house with a trimmed lawn, a "
        "concrete front path, a small porch with a front door, flower beds and a curtained picture "
        "window. The Major walks up the path toward the front door, seen from behind at a "
        "three-quarter angle, his whole figure small in the frame, helmet and tunic recognisable. "
        "No other people. Soft daylight."),
    "P11_laura_door_mcu": (
        [ep("ep09_p1_borrow_your_muscles"), ep("ep09_p2_honeymoon_present")],
        "The Pritchards' front door seen from the porch. Medium close-up of Laura alone standing "
        "in the open doorway, one hand on the edge of the door, leaning out a little, a bright "
        "welcoming smile. The hall and living room soft behind her. " + CU.format(side="right")),
    "P12_major_step_mcu": (
        [ep("ep09_p1_borrow_your_muscles"), COVER],
        "The Pritchards' porch seen from inside the open front door. Medium close-up of the Major "
        "alone on the doorstep, head, helmet and shoulders filling the frame, daylight and lawn "
        "soft behind him. Attentive, pleased to be asked. Eyes and mouth clearly visible under the "
        "helmet brim. " + CU.format(side="left")),
    # --- episode 9: the clown ---
    "P13_laura_table_cu": (
        [ep("ep09_p2_honeymoon_present"), ep("ep09_p3_delicate_things")],
        "Pritchard living room. Close-up of Laura alone standing beside the side table and lamp, "
        "head and shoulders filling the frame, turned a little toward camera right, a sweet "
        "carefully innocent smile. The framed wedding photo soft on the wall behind. THE CLOWN is "
        "out of frame. " + CU.format(side="right")),
    "P14_major_standing_cu": (
        [ep("ep09_p3_delicate_things"), COVER, ep("ep09_p2_honeymoon_present")],
        "Pritchard living room. Tight close-up of the Major alone, standing, head, helmet and "
        "shoulders filling the frame, floral wallpaper and lamp glow soft behind him. Calm, "
        "slightly abashed. Eyes and mouth clearly visible under the helmet brim. THE CLOWN is out "
        "of frame. " + CU.format(side="left")),
    "P15_laura_cheeks_cu": (
        [ep("ep09_p4_honeymoon_clown"), ep("ep09_p5_bear_up_somehow")],
        "Pritchard living room. Close-up of Laura alone, head and shoulders, both hands pressed to "
        "her cheeks with the fingertips at her chin, mouth closed and fully visible, eyes wide and "
        "shining, barely hiding delight, looking down a little toward camera left at something "
        "off-frame. Lamp glow and floral wallpaper soft behind. Nobody else in frame."),
    # --- episode 9: tea ---
    "P16_sofa_tea_twoshot": (
        [ep("ep09_p5_bear_up_somehow"), COVER, ep("ep09_p2_honeymoon_present")],
        "Pritchard living room, later. Medium two-shot on the floral sofa: the Major seated on the "
        "left holding a flowered teacup and saucer in both hands, Laura seated close beside him on "
        "the right, turned toward him, one hand resting on his shoulder, warm and attentive. A tea "
        "tray with a teapot, a second cup and a plate of biscuits on the coffee table in the "
        "foreground. Side table and lamp behind. THE CLOWN is absent, already broken and cleared "
        "away; nothing on the side table but the lamp."),
    "P17_laura_sofa_cu": (
        [ep("ep09_p5_bear_up_somehow"), ep("ep09_p2_honeymoon_present")],
        "Pritchard living room. Close-up of Laura alone seated on the floral sofa, head and "
        "shoulders filling the frame, turned a little toward camera left, a sweet carefully "
        "innocent smile. Lamp glow soft behind. No figurine anywhere in frame. "
        + CU.format(side="left")),
    # --- episode 9: the button ---
    "P18_door_leaving_twoshot": (
        [ep("ep09_p6_anniversary_figurine"), ep("ep09_p1_borrow_your_muscles"), COVER],
        "The Pritchards' front hall seen from inside. Medium two-shot: the Major on the left has "
        "one boot over the threshold of the open front door and is turning his head back; Laura on "
        "the right stands by a small hall table, pointing with one finger at THE FIGURINE, which "
        "stands on the hall table at the right edge of frame. Daylight through the open door."),
    "P19_laura_figurine_mcu": (
        [ep("ep09_p6_anniversary_figurine"), ep("ep09_p2_honeymoon_present")],
        "The Pritchards' front hall. Medium close-up of Laura alone beside the hall table, THE "
        "FIGURINE on the table in the lower corner of the frame beside her, her hand resting "
        "lightly on the table near it. A sweet, innocent, hopeful smile. Daytime: bright daylight "
        "and the lawn through the open front door soft behind her, no night sky. " + CU.format(side="left")),
    "P20_major_porch_mcu": (
        [ep("ep09_p6_anniversary_figurine"), COVER, ep("ep09_p1_borrow_your_muscles")],
        "The Pritchards' porch, daylight. Medium close-up of the Major alone, head, helmet and "
        "shoulders, turned back over his shoulder toward the doorway, face brightening with eager "
        "willingness. Lawn and street soft behind him. Eyes and mouth clearly visible under the "
        "helmet brim. " + CU.format(side="right")),
    # --- episode 14: the pool table ---
    "P21_organ_room_wide": (
        [ep("ep14_p1_pool_table_sale"), ep("ep14_p2_stopped_turning"), ep("ep14_p3_anything_valuable")],
        EP14 + "Pritchard living room, the organ wall. Wide shot: the home organ with its bench against "
        "the wall at centre right, the sheet-music book open on its stand; above it the wooden wall "
        "shelf holding, left to right, THE FAN, THE TROPHY, THE BALL and THE BOBBLEHEAD, all "
        "clearly visible. Rob stands at the left holding up THE FLYER with both hands, grinning and "
        "eyeing the organ; Laura stands beside him with her arms folded, unmoved, a small smile. "
        "The Major is NOT in this shot."),
    "P22_rob_flyer_mcu": (
        [ep("ep14_p1_pool_table_sale"), ep("ep14_p6_three_keyboards")],
        EP14 + "Pritchard living room, the organ wall. Medium close-up of Rob alone, head and shoulders, "
        "holding THE FLYER up at chest height in one hand with its headline toward camera, a big "
        "hopeful grin. The organ soft behind him. " + CU.format(side="right")),
    "P23_laura_armsfolded_mcu": (
        [ep("ep14_p1_pool_table_sale"), ep("ep14_p6_three_keyboards")],
        EP14 + "Pritchard living room, the organ wall. Medium close-up of Laura alone, arms folded, chin "
        "up, a sweet immovable smile. The organ and the wall shelf soft behind her. "
        + CU.format(side="left")),
    # --- episode 14: the fan ---
    "P24_rob_fan_mcu": (
        [ep("ep14_p2_stopped_turning"), ep("ep14_p3_anything_valuable")],
        EP14 + "Pritchard living room, the wall shelf. Medium close-up of Rob alone, head and shoulders, "
        "pointing up with one finger at THE FAN, which sits still on the shelf above him at the "
        "top left of the frame beside THE TROPHY. Cheerful, a little too casual. "
        + CU.format(side="right")),
    "P25_major_fan_mcu": (
        [ep("ep14_p2_stopped_turning"), COVER, ep("ep14_p3_anything_valuable")],
        EP14 + "Pritchard living room, the wall shelf. Medium close-up of the Major alone, head, helmet "
        "and shoulders, one hand raised to his chin, THE FAN sitting still on the shelf at the top "
        "right of the frame. Thoughtful. Eyes and mouth clearly visible under the helmet brim. "
        + CU.format(side="left")),
    "P26_bobblehead_insert": (
        [ep("ep14_p3_anything_valuable"), ep("ep14_p2_stopped_turning")],
        EP14 + "Pritchard living room, the wall shelf. Close insert: Rob's hands, tan cardigan cuffs and "
        "the end of his black tie in frame, no face, lifting THE BOBBLEHEAD off the wooden shelf; "
        "THE BALL and the base of THE TROPHY beside it on the shelf. The top of the organ soft "
        "below."),
    "P27_rob_bobblehead_mcu": (
        [ep("ep14_p3_anything_valuable"), ep("ep14_p5_fix_the_fan")],
        EP14 + "Pritchard living room, the organ wall. Medium close-up of Rob alone, head and shoulders, "
        "cradling THE BOBBLEHEAD against his chest with one hand, a cheerful conspiratorial grin. "
        "The shelf soft behind. " + CU.format(side="right")),
    # --- episode 14: the chain ---
    "P28_fan_touch_insert": (
        [ep("ep14_p4_whirr-klack!"), ep("ep14_p3_anything_valuable")],
        EP14 + "Pritchard living room, the wall shelf. Close insert on the shelf: the Major's furry hand "
        "with its grey tunic cuff touches the wire cage of THE FAN at the left; THE TROPHY stands "
        "immediately to its right and THE BALL beyond it near the right end of the shelf, all "
        "three on the shelf. No faces. The fan is still, the moment before it starts."),
    "P29_trophy_ball_insert": (
        [ep("ep14_p4_whirr-klack!")],
        EP14 + "Pritchard living room, the wall shelf. Close insert: THE FAN at the left spins in a blur "
        "and has tipped against THE TROPHY, which is toppling sideways to the right and striking "
        "THE BALL; the ball has just begun to roll toward the right end of the shelf. No people in "
        "frame."),
    "P30_ball_drops_insert": (
        [ep("ep14_p4_whirr-klack!"), ep("ep14_p5_fix_the_fan")],
        EP14 + "Pritchard living room. Medium insert from just below the shelf: THE BALL rolls off the "
        "right end of the wooden wall shelf and drops through the air, THE TROPHY lying on its "
        "side on the shelf behind it; directly beneath, the top of the organ with its sheet-music "
        "book. No people in frame."),
    "P31_organ_crushed_wide": (
        [ep("ep14_p5_fix_the_fan"), ep("ep14_p4_whirr-klack!"), COVER],
        EP14 + "Pritchard living room, the organ wall. Wide shot: the home organ has collapsed into a "
        "heap of splintered brown wood, scattered white and black keys and the sheet-music book, "
        "THE BALL sitting in the middle of the wreck. The Major stands at the left of the wreck "
        "with his hands half raised, startled; Rob stands beside him at the far left clutching THE "
        "BOBBLEHEAD to his chest, mouth open in mock horror. On the shelf above, THE FAN still "
        "spinning and THE TROPHY on its side."),
    # --- episode 14: aftermath ---
    "P32_rob_wreck_mcu": (
        [ep("ep14_p5_fix_the_fan"), ep("ep14_p6_three_keyboards")],
        EP14 + "Pritchard living room. Medium close-up of Rob alone, head and shoulders, THE BOBBLEHEAD "
        "clutched to his chest with one hand, eyebrows up in a mock dismay that cannot hide his "
        "pleasure. The wrecked organ soft behind him. " + CU.format(side="right")),
    "P33_laura_arrives_wide": (
        [ep("ep14_p6_three_keyboards"), ep("ep14_p5_fix_the_fan"), COVER],
        EP14 + "Pritchard living room. Medium wide shot: Laura has just come in through the doorway at "
        "the right, one hand to her chest, taking in the wrecked organ, a heap of splintered wood "
        "and keys in the left foreground; the Major stands beyond the wreck at the left, hands "
        "clasped sheepishly, Rob beside him holding THE BOBBLEHEAD. Her face is lighting up."),
    "P34_laura_wreck_mcu": (
        [ep("ep14_p6_three_keyboards"), ep("ep09_p5_bear_up_somehow")],
        EP14 + "Pritchard living room. Medium close-up of Laura alone, head and shoulders, hands clasped "
        "together under her chin, delighted, a bright sweet smile. The wrecked organ soft behind "
        "her. " + CU.format(side="left")),
    "P35_trio_wreck": (
        [ep("ep14_p6_three_keyboards"), ep("ep14_p5_fix_the_fan"), COVER],
        EP14 + "Pritchard living room. Medium three-shot over the wrecked organ in the foreground: Rob at "
        "the left holding THE FLYER in one hand and THE BOBBLEHEAD in the other, bright; Laura in "
        "the middle, one hand on her hip, beaming; the Major at the right with his hands clasped "
        "together in front of his belt, pleased, shy, proud to have helped. On the shelf above, "
        "THE FAN and THE TROPHY on its side."),
    # --- tag ---
    "P36_ext_house_dusk": (
        [ep("ep09_p1_borrow_your_muscles"), ep("ep09_p6_anniversary_figurine"),
         ep("ep14_p1_pool_table_sale"), COVER],
        "Exterior, dusk. The tidy white 1960s suburban house seen from the street, warm light in "
        "its two front windows. The Major walks toward camera down the front path, in frame from "
        "the waist up, content, mouth closed. Behind him, through the left window, Laura stands "
        "holding THE FIGURINE and looking at it; through the right window, Rob stands looking up "
        "at a tall fringed floor lamp. Street-lamp glow, early-evening sky."),
}


def make(client: OpenAI, out: pathlib.Path, pid: str) -> str:
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
    return pid


def main(argv: list[str]) -> None:
    root = pathlib.Path(argv[0])
    out = root / "out"
    out.mkdir(parents=True, exist_ok=True)
    ids = list(PLATES) if argv[1:] == ["all"] else argv[1:]
    todo = []
    for pid in ids:
        if (out / f"{pid}.png").exists():
            print("exists", pid, flush=True)
        else:
            todo.append(pid)
    client = OpenAI()
    with concurrent.futures.ThreadPoolExecutor(max_workers=JOBS) as pool:
        futures = {pool.submit(make, client, out, pid): pid for pid in todo}
        for fut in concurrent.futures.as_completed(futures):
            pid = futures[fut]
            try:
                print("wrote", out / f"{fut.result()}.png", flush=True)
            except Exception as exc:  # keep the other plates rendering
                print("FAILED", pid, repr(exc), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
