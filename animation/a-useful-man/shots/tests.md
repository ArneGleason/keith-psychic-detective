# Test battery: three shots from episode 9

Purpose: prove the voiced pipeline on the hardest face before any scale-up.
All three sit inside *A Useful Man*, so a pass is also a finished shot.

Plates come from `animation/tools/plates.py` (clean, 16:9, no lettering).
Voices come from `animation/tools/voice_cast.py` (placeholder casting).
Kling: image-to-video from the plate as the START frame only. Never a video
frame as a start frame. One action per shot. End on a held pose.

| Test | Start plate | Duration | One action | Proves |
|---|---|---|---|---|
| T1 | P1_doorway_twoshot | 5 s | Laura gestures to the clown; the Major steps in and lifts it with both hands, very carefully; Laura's hands rise to her chin | two-character exchange, hands, costume stability |
| T2a | P2_major_holds_clown | 5 s | The clown slips from his hands, falls onto the coffee table and shatters, spring and shards | the physical gag: contact and consequence |
| T2b | P3_aftermath | 4 s | Nothing moves but faces: the Major's jaw drops, Laura's hands cover her mouth, her eyes crinkle | reaction timing on a locked camera |
| T3a | P5_laura_closeup_crop | 6 s, lip sync | Laura says her line (placeholder voice `laura`) | human lip sync, baseline |
| T3b | P4_major_closeup | 6 s, lip sync | The Major says his line (placeholder voice `major`) | lip sync on a 1970s ape mask: the real question |

Plate notes (2026-10-19): P1, P2, P3 approved for the tests. P4 is the second
render (the first, `_v1_wide`, had the unbroken clown beside him). P5 twice
came back as a two-shot with the clown intact, so `P5_laura_closeup_crop` is a
2x upscaled crop of the second render; good enough for the sync test, not for
the film. For the film, every post-break plate needs the clown out of the lock
block.

## Dialogue for T3 (from the page)

- Laura: "My husband gave me this on our honeymoon. It really deserves a more prominent position."
- Major: "I'm not very good with delicate things."

Rendered with the cast voices by `tools/lines.py` from `shots/lines.json`:
`voices/lines/T3a_laura.wav` (4.75 s) and `voices/lines/T3b_major.wav` (3.15 s).
If the casting changes, delete them and re-run; the file names stay.

## Kling prompts

Paste as written. Model and mode: whatever the signed-in account offers for
image-to-video at 16:9 (Kling 4.0 if available, else 2.x Pro). Start frame =
the plate. No end frame.

**T1**
> A 1960s sitcom living room. The woman in the light-blue sweater gestures to the ceramic clown figurine on the side table. The stocky ape in the grey military tunic and steel helmet steps in and lifts the figurine with both hands, slowly and very carefully, holding it against his chest. She clasps her hands under her chin and watches the figurine. Camera locked, eye level. Natural, restrained movement. Faces, costumes and helmet stay exactly as in the image. No text.

**T2a**
> The ceramic clown figurine slips out of the ape's hands, drops onto the coffee table and shatters into ceramic shards; a small metal spring bounces out. The ape in the steel helmet freezes with his hands still raised. The woman beside him flinches. Camera locked. No text, no sound-effect lettering.

**T2b**
> Locked camera, nothing in the room moves except the two faces. The ape in the steel helmet slowly opens his mouth in dismay and looks from the broken figurine up to the woman. The woman raises both hands to cover her mouth; her eyes crinkle with delight she is trying to hide. Subtle, slow, natural. No text.

**T3a / T3b**
> Image-to-video, 6 s: "Close-up, locked camera, the character breathes and blinks naturally, small head movement, looking at someone just off camera. No text." Then Lip Sync on the result: Upload local dubbing, the line's WAV, Add Speech at 0:00, Generate. Download via the Download button.

## Pass / fail

- T1 and T2: faces, helmet and costume hold; hands have five digits; the
  figurine does not change shape; no lettering appears. Motion is
  restrained, not floating.
- T3b: the mask's mouth moves on the syllables and the face stays a mask
  (no morph toward a human or a real gorilla). If this fails, try Kling
  Avatar on P4 with the same WAV, and if that fails too the Major's dialogue
  goes off-screen or onto reaction shots.

## Log

Record every run in `log/kling.md`: date, test id, model/mode, plate, prompt
hash, credits before/after, result file name, verdict.

## Results (2026-10-19, Kling 4.0, Chrome session)

| Test | Verdict | Note |
|---|---|---|
| T1 | PASS | two-character exchange holds; the Major's lift is slow and careful as asked |
| T2a | PASS | clown bursts in his hands at ~1.5 s, spring flies; good gag beat |
| T2b | PASS | reaction only, camera locked; subtle, usable |
| T3a | PASS | Laura's lip sync is clean |
| T3b | PARTIAL | mask mouth moves but only a few pixels; reads as mumbling, not speech |

Downloaded files: `clips/*.mp4` (Kling's 1080p re-encode) and `clips/orig/*.mp4`
(the source encode, slightly larger frame). Contact sheets in `clips/review/`.

| T3b Avatar | PASS | Kling Avatar (image + WAV, 24 credits) gives full mouth shapes on the mask; this is the dialogue tool for the apes |

**Decision from the battery:** ape dialogue close-ups go through Kling Avatar
from the clean plate plus the line WAV (one still, one line, no base clip
needed). Human dialogue can use either tool. Physical gags and two-shots go
through Kling 4.0 Keyframes from the plate. Reaction shots: Keyframes with a
faces-only prompt. All of this at 1080p, 5 s, adaptive ratio.
