# Kling generation log: Under Pressure experiment (2026-10-19)

Kling 4.0, Keyframes mode (first frame only), 1080p, adaptive ratio, one
output. Credits read from the sidebar/Credit Details, never estimated.

| Time | Shot | Plate | Length | Credits | Result | Verdict |
|---|---|---|---|---|---|---|
| 17:00 | S1 | P1_caffeine | 5 s | 67 | clips/S1.mp4 (1924x1076) | PASS: painted look holds, packet shaken, shrug, Boggler hunched; mouths move on the lines |
| 17:01 | S2 | P1b_prof_boggler_crop (2x upscaled crop) | 5 s | 67 | clips/rejects/S2_v1_text_only.mp4 (1920x1080) | REJECT: plate ignored, generic flat anime apes at a bar |
| 17:01 | S3 | P2_plumber | 5 s | 67 | clips/S3.mp4 (1924x1076) | PASS: plumber lifts the toolbox and exits, Boggler hunched, Count slumped |
| 17:01 | S4 | P2b_count_armchair_crop (2x upscaled crop) | 5 s | 67 | clips/rejects/S4_v1_text_only.mp4 (1920x1080) | REJECT: plate ignored, anime gorilla in a throne |
| 17:03 | S5 | P3_bubble_house | 10 s | 135 | clips/S5.mp4 (1924x1076) | PASS: bubble swells and settles over the house, rainbow ripple, plumber still; lovely |
| 17:05 | S6 | P4_four_hours | 5 s | 67 | clips/S6.mp4 (1924x1076) | PASS: Major strains at the wall, ripples spread from his palms, the two behind react |
| 17:05 | S7 | P5_one_push | 5 s | 67 | clips/S7.mp4 (1924x1076) | PASS: shove, bulge, spring-back; the Major's face squashes |
| 17:06 | S8 | P6_smell | 5 s | 67 | clips/rejects/S8_v1_text_only.mp4 (1920x1080) | REJECT: plate ignored, generic flat anime apes |

Credit Details: 16145 before the experiment, 15340 after all eleven jobs = 805 spent (10 x 67 + 135), including the three text-only rejects (201).
| 17:19 | S2 v2 | P1b_prof_boggler (Gemini re-frame, launched from the home composer, thumbnail verified) | 5 s | 67 | clips/S2.mp4 (1924x1076) | PASS: Boggler grimaces and clutches his stomach, Professor glances sideways, painted look holds |
| 17:20 | S4 v2 | P2b_count_armchair (Gemini re-frame, grid composer, thumbnail verified) | 5 s | 67 | clips/S4.mp4 (1924x1076) | PASS: Count sags, eyes close, mouth drops open, slow push in |
| 17:21 | S8 v2 | P6_smell (grid composer, 10 s wait, thumbnail verified) | 5 s | 67 | clips/S8.mp4 (1924x1076) | PASS: all three recoil, hand over nose, Professor waves, Major hunches and glances back |

Lesson: three of eight jobs ran as text-to-video. The First-frame slot still
showed its upload spinner when Generate was clicked (visible in the S8
screenshot), so the plate had not registered. Diagnostic: an output of exactly
1920x1080 means the plate was ignored; 1924x1076 means image-to-video ran.
Rule: after file_upload, wait and zoom on the slot until the thumbnail shows
the plate before submitting. Also: 2x-upscaled crops are not needed; Gemini
re-frames of the painted panel (P1b_prof_boggler, P2b_count_armchair) are
cleaner plates.
