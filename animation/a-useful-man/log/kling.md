# Kling generation log: A Useful Man

Credits are read from the account page before and after each run, never
estimated. One row per generated clip, including rejects.

| Date | Test/shot | Tool, model, mode | Start plate | Audio | Credits before → after | Result file | Verdict |
|---|---|---|---|---|---|---|---|
| 2026-10-19 | T1 | Kling 4.0, Keyframes (first frame only), 1080p, 5 s, adaptive ratio, 1 output | P1_doorway_twoshot | none | 16514 → 16447 (67.00 per 5 s 1080p job on Ultra, Kling 4.0 10% off) | clips/T1_doorway_twoshot.mp4 (orig/ = 1764x1176 source) | PASS: Laura gestures, Major steps in and lifts the clown with both hands, her hands rise to her chin; faces, helmet, costume hold; no lettering |
| 2026-10-19 | T2a | same | P2_major_holds_clown | none | 16447 → 16380 | clips/T2a_clown_shatters.mp4 | PASS: clown bursts in his hands at ~1.5 s (spring and shards), Major freezes hands up, Laura flinches then clasps; it shatters in-hand rather than on the table, which is fine |
| 2026-10-19 | T2b | same | P3_aftermath | none | 16380 → 16313 | clips/T2b_aftermath_reaction.mp4 | PASS: locked camera, Major's jaw drops and he looks up to her, Laura's hands cover her mouth, eyes crinkle; subtle |
| 2026-10-19 | T3b base | same, "breathes and blinks" prompt | P4_major_closeup | none yet (lip sync next) | 16313 → 16246 | clips/T3b_major_base.mp4 | OK as a sync base (breath, blink, small head turn, mouth stays shut) |
| 2026-10-19 | T3a base | same, "breathes and blinks" prompt | P5_laura_closeup_crop | none yet (lip sync next) | 16246 → 16179 (Credit Details page, 15:23) | clips/T3a_laura_base.mp4 | OK as a sync base |
| 2026-10-19 | T3b lip sync | Kling Lip Sync, Upload Local Dubbing, on the T3b base clip | (T3b base clip) | voices/lines/T3b_major.wav (3.15 s) | 16179 → 16174 (5.00) | clips/T3b_major_lipsync.mp4 (1760x1168, has audio) | PARTIAL: the mask's lips part a few pixels on two or three syllables (~0.4 s, ~1.8 s), face stays a mask, no morph; too small to read as speech. See review/T3b_mouth_A.png, _B.png |
| 2026-10-19 | T3a lip sync | same, on the T3a base clip | (T3a base clip) | voices/lines/T3a_laura.wav (4.75 s) | 16174 → 16169 (5.00) | clips/T3a_laura_lipsync.mp4 | PASS: clear mouth shapes on the syllables, teeth visible, face holds |
| 2026-10-19 | T3b Avatar fallback | Kling Avatar (image + audio), 1080p, performance note "speaks earnestly, clear mouth movement, small nod, teacup still" | P4_major_closeup (from Uploads) | voices/lines/T3b_major.wav | 16169 → 16145 (24.00, confirmed on Credit Details 15:47) | clips/T3b_major_avatar.mp4 (3.2 s, 1760x1168, audio; orig/ has the source encode) | PASS: wide, readable mouth shapes on every syllable, mask texture and helmet hold, no morph toward a human face, small nod, teacup still. See review/T3b_avatar_mouth.png |

Session total 2026-10-19: 16514 → 16145, 369 credits for 8 clips.
